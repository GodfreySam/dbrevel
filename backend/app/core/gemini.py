"""Gemini AI Engine for query generation

Copyright (c) 2026 Godfrey Samuel
Licensed under the MIT License - see LICENSE file for details

Migrated to google.genai package (replaces deprecated google.generativeai).
Requires Python 3.10+.
"""
import json
import logging
import re
from typing import Any, Dict, List

from app.core.accounts import AccountConfig
from app.core.config import settings
from app.core.exceptions import (GeminiAPIError, GeminiResponseError,
                                 InvalidJSONError, InvalidQueryPlanError,
                                 MissingBYOApiKeyError)
from app.core.retry import retry_with_exponential_backoff
from app.models.query import DatabaseQuery, QueryPlan, SecurityContext
from app.models.schema import DatabaseSchema
from google.genai import Client
from google.genai.types import GenerateContentConfig

logger = logging.getLogger(__name__)


class GeminiEngine:
    """Core Gemini integration for query generation and reasoning"""

    def __init__(self, api_key: str, model_name: str):
        # Use new google.genai Client API
        self.client = Client(api_key=api_key)
        self.model_name = model_name
        # Create generation config for consistent query generation
        self.generation_config = GenerateContentConfig(
            temperature=0.1,  # Low for consistency
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
        )

    async def generate_query_plan(
        self,
        intent: str,
        schemas: Dict[str, DatabaseSchema],
        security_ctx: SecurityContext
    ) -> QueryPlan:
        """Generate complete query execution plan from intent

        Uses retry logic with exponential backoff for transient Gemini API failures.

        Args:
            intent: Natural language query intent
            schemas: Available database schemas
            security_ctx: Security context for query generation

        Returns:
            QueryPlan with generated queries

        Raises:
            GeminiResponseError: If Gemini response is invalid
            GeminiAPIError: If Gemini API fails after all retries
        """

        prompt = self._build_query_prompt(intent, schemas, security_ctx)

        # Wrap Gemini API call with retry logic
        async def _call_gemini():
            logger.debug(
                f"Calling Gemini API for query generation. Intent: {intent[:100]}...")
            return await self.client.aio.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=self.generation_config
            )

        try:
            # Retry on network errors, timeouts, and rate limits
            # Don't retry on invalid responses (those are user/prompt errors)
            response = await retry_with_exponential_backoff(
                _call_gemini,
                max_retries=3,
                initial_delay=1.0,
                max_delay=10.0,
                exceptions=(ConnectionError, TimeoutError,
                            OSError),  # Network-related errors
            )
        except Exception as e:
            logger.error(
                f"Gemini API call failed after retries: {e}", exc_info=True)
            raise GeminiAPIError(f"Gemini API call failed after retries: {e}")

        # Extract text from response (new API structure)
        # response.candidates[0].content.parts[0].text
        if not response.candidates:
            raise GeminiResponseError("No candidates in Gemini response")

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise GeminiResponseError("No content parts in Gemini response")

        # Extract text from all parts (in case there are multiple)
        text_parts = [
            part.text for part in candidate.content.parts if part.text]
        if not text_parts:
            raise GeminiResponseError(
                "No text content in Gemini response parts")

        # Join text parts, preserving newlines might help with JSON structure
        response_text = "\n".join(text_parts).strip()

        # Log raw response for debugging (truncated to avoid spam)
        logger.debug(
            f"Gemini raw response (first 500 chars): {response_text[:500]}")

        # Extract JSON from response - handle multiple formats
        plan_data = self._extract_json_from_response(response_text)

        # Normalize query_type values from Gemini response
        # Gemini may return "aggregation" or other values, but we need "sql", "mongodb", or "cross-db"
        if "queries" in plan_data and isinstance(plan_data["queries"], list):
            for query in plan_data["queries"]:
                database = query.get("database", "").lower()
                query_value = query.get("query")
                query_type = query.get("query_type", "").lower(
                ) if query.get("query_type") else ""

                # Determine correct query_type based on database and query structure
                if query_type == "mongodb":
                    query["query_type"] = "mongodb"
                elif query_type == "cross-db" or query_type == "cross_db":
                    query["query_type"] = "cross-db"
                elif query_type == "sql":
                    query["query_type"] = "sql"
                # Normalize "aggregation" and other MongoDB-related terms
                elif query_type in ["aggregation", "mongo", "nosql"]:
                    query["query_type"] = "mongodb"
                # Infer from query structure: MongoDB uses arrays/pipelines
                elif isinstance(query_value, list):
                    query["query_type"] = "mongodb"
                # Infer from query content: check for MongoDB operators
                elif isinstance(query_value, str) and any(
                    op in query_value for op in ["$match", "$group", "$project", "$limit", "$sort", "$lookup"]
                ):
                    query["query_type"] = "mongodb"
                # Infer from database type
                elif database == "mongodb":
                    query["query_type"] = "mongodb"
                elif database == "postgres" or database.startswith("postgres"):
                    query["query_type"] = "sql"
                # Final fallback: default based on query structure
                else:
                    query["query_type"] = "mongodb" if isinstance(
                        query_value, list) else "sql"

        # Create QueryPlan from response with validation
        try:
            plan = QueryPlan(**plan_data)
        except Exception as e:
            raise InvalidQueryPlanError(
                f"Failed to create QueryPlan from Gemini response. "
                f"Data: {plan_data} "
                f"Error: {str(e)}"
            )

        return plan

    async def validate_query(
        self,
        query: DatabaseQuery,
        schema: DatabaseSchema
    ) -> Dict[str, Any]:
        """Use Gemini to validate query safety"""

        validation_prompt = f"""
You are a database security expert. Validate this query for safety and correctness.

QUERY TYPE: {query.query_type}
QUERY: {query.query}
SCHEMA: {schema.model_dump_json()}

Check for:
1. SQL/NoSQL injection vulnerabilities
2. Dangerous operations (DROP, TRUNCATE, DELETE without WHERE)
3. Performance issues (missing indexes, full table scans)
4. Schema mismatches
5. Missing constraints

Return JSON:
{{
    "safe": true/false,
    "issues": ["list of issues found"],
    "severity": "low/medium/high",
    "suggestions": ["performance/security suggestions"],
    "estimated_cost": "low/medium/high"
}}
"""

        # Use async API from google.genai
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=validation_prompt,
            config=self.generation_config
        )

        # Extract text from response (new API structure)
        if not response.candidates:
            raise GeminiResponseError("No candidates in Gemini response")

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            raise GeminiResponseError("No content parts in Gemini response")

        # Extract text from all parts (in case there are multiple)
        text_parts = [
            part.text for part in candidate.content.parts if part.text]
        if not text_parts:
            raise GeminiResponseError(
                "No text content in Gemini response parts")

        response_text = "\n".join(text_parts).strip()

        # Use the same robust JSON extraction method
        try:
            validation_data = self._extract_json_from_response(response_text)
            return validation_data
        except Exception as e:
            logger.error(f"Failed to parse validation response: {e}")
            logger.error(f"Validation response text: {response_text[:500]}")
            # Return a safe default if parsing fails
            return {"safe": False, "issues": [f"Failed to parse validation: {str(e)}"], "severity": "high"}

    def _extract_json_from_response(self, response_text: str) -> dict:
        """
        Extract JSON from Gemini response, handling various formats.

        Handles:
        - Markdown code blocks (```json ... ```)
        - Plain JSON
        - JSON with extra text before/after
        - Multiple JSON objects (returns first valid one)
        """
        # Remove markdown code blocks if present
        if "```json" in response_text:
            # Extract content between ```json and ```
            match = re.search(r'```json\s*(.*?)\s*```',
                              response_text, re.DOTALL)
            if match:
                response_text = match.group(1).strip()
        elif "```" in response_text:
            # Extract content between ``` and ```
            match = re.search(r'```\s*(.*?)\s*```', response_text, re.DOTALL)
            if match:
                response_text = match.group(1).strip()

        # Find the start of JSON (first opening brace)
        json_start = response_text.find('{')
        if json_start == -1:
            raise InvalidJSONError(
                f"No JSON object found in response: {response_text[:200]}...")

        # Extract just the first complete JSON object by finding balanced braces
        # This handles "Extra data" errors by only extracting the first valid JSON object
        json_text = response_text[json_start:]

        # Find the first complete JSON object by counting braces
        # This approach handles strings containing braces correctly
        brace_count = 0
        json_end_idx = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(json_text):
            if escape_next:
                escape_next = False
                continue
            if char == '\\':
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_end_idx = i + 1
                        break

        # Extract just the JSON portion (first complete object)
        if brace_count == 0 and json_end_idx > 0:
            json_object_text = json_text[:json_end_idx].strip()
        else:
            # If braces don't balance, try to find the last } as fallback
            last_brace = json_text.rfind('}')
            if last_brace > 0:
                json_object_text = json_text[:last_brace+1].strip()
            else:
                json_object_text = json_text.strip()

        # Clean up trailing commas
        json_object_text = self._clean_json_text(json_object_text)

        # Now parse the extracted JSON object
        try:
            return json.loads(json_object_text)
        except json.JSONDecodeError as e:
            logger.warning(
                f"JSON parse failed after extraction: {str(e)}. Trying raw_decode...")

            # Fallback: try raw_decode as it might handle some edge cases better
            try:
                decoder = json.JSONDecoder()
                plan_data, idx = decoder.raw_decode(json_object_text)
                return plan_data
            except json.JSONDecodeError:
                pass
            # If direct parsing failed, try cleaning trailing commas and other issues
            json_text_cleaned = self._clean_json_text(json_text)
            try:
                decoder = json.JSONDecoder()
                plan_data, idx = decoder.raw_decode(json_text_cleaned)
                return plan_data
            except json.JSONDecodeError:
                pass

            # If that also failed, the JSON might be malformed
            # If raw_decode failed, the JSON might be malformed
            # Try a more lenient approach: find and extract the JSON object manually
            # Sometimes Gemini includes explanatory text that breaks the JSON structure

            # Try to extract JSON by finding balanced braces from the start
            # This handles cases where there might be invalid characters before the JSON
            cleaned_text = response_text[json_start:].strip()

            # Remove any leading/trailing non-JSON characters
            # Sometimes Gemini adds prefixes like "Here's the query:" or similar
            json_match = re.search(r'(\{.*\})', cleaned_text, re.DOTALL)
            if json_match:
                json_candidate = json_match.group(1)
                json_candidate = self._clean_json_text(json_candidate)
                try:
                    decoder = json.JSONDecoder()
                    plan_data, idx = decoder.raw_decode(json_candidate)
                    return plan_data
                except json.JSONDecodeError:
                    pass

            # Last resort: try to fix common JSON issues and parse
            # Remove comments, fix trailing commas, etc.
            try:
                # Try removing any lines that look like comments or explanations
                lines = cleaned_text.split('\n')
                json_lines = []
                brace_count = 0
                started = False

                for line in lines:
                    stripped = line.strip()
                    # Skip comment-like lines (but be careful - JSON strings might contain //)
                    if stripped.startswith('//') and not started:
                        continue
                    if '{' in line:
                        started = True
                    if started:
                        json_lines.append(line)
                        brace_count += line.count('{') - line.count('}')
                        if brace_count == 0 and '{' in line:
                            break

                if json_lines:
                    json_candidate = '\n'.join(json_lines)
                    json_candidate = self._clean_json_text(json_candidate)
                    decoder = json.JSONDecoder()
                    plan_data, idx = decoder.raw_decode(json_candidate)
                    return plan_data
            except (json.JSONDecodeError, ValueError):
                pass

            # Log the full response for debugging
            logger.error(f"JSON parsing failed. Error: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error(
                f"Full response text ({len(response_text)} chars):\n{response_text}")
            logger.error(f"JSON start position: {json_start}")
            logger.error(
                f"JSON text attempted ({len(json_text)} chars):\n{json_text[:1000]}")

            # Try one more time with a more aggressive approach: find the first complete JSON object
            # by counting braces more carefully
            try:
                # Find first { and last } that balance out
                first_brace = json_text.find('{')
                if first_brace != -1:
                    brace_count = 0
                    last_valid_idx = first_brace
                    in_string = False
                    escape_next = False
                    for i, char in enumerate(json_text[first_brace:], start=first_brace):
                        if escape_next:
                            escape_next = False
                            continue
                        if char == '\\':
                            escape_next = True
                            continue
                        if char == '"' and not escape_next:
                            in_string = not in_string
                        if not in_string:
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    last_valid_idx = i + 1
                                    break

                    if brace_count == 0 and last_valid_idx > first_brace:
                        json_candidate = json_text[first_brace:last_valid_idx]
                        decoder = json.JSONDecoder()
                        plan_data, idx = decoder.raw_decode(json_candidate)
                        logger.info(
                            f"Successfully parsed JSON using aggressive extraction")
                        return plan_data
            except Exception as inner_e:
                logger.error(f"Aggressive extraction also failed: {inner_e}")

            raise InvalidJSONError(
                f"Failed to parse JSON from Gemini response. "
                f"Error: {str(e)}. "
                f"Response length: {len(response_text)} chars. "
                f"First 500 chars: {response_text[:500]}"
            )

    def _clean_json_text(self, json_text: str) -> str:
        """Clean JSON text by removing trailing commas and fixing common issues."""
        # Remove trailing commas before closing braces/brackets (but be careful)
        # This regex is more conservative - only removes trailing commas in objects/arrays
        json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)
        return json_text.strip()

    def _build_query_prompt(
        self,
        intent: str,
        schemas: Dict[str, DatabaseSchema],
        security_ctx: SecurityContext
    ) -> str:
        """Build comprehensive prompt for query generation."""

        schemas_json = {name: schema.model_dump()
                        for name, schema in schemas.items()}

        # Optimized shorter prompt
        schemas_str = json.dumps(
            schemas_json, separators=(",", ":"))  # Compact JSON

        return f"""
Generate optimized database query from user intent.

SCHEMAS:
{schemas_str}

CONTEXT: role={security_ctx.role}, org={security_ctx.account_id}, perms={security_ctx.permissions}
FILTERS: {json.dumps(security_ctx.row_filters, separators=(",", ":"))}
MASKS: {json.dumps(security_ctx.field_masks, separators=(",", ":"))}

INTENT: "{intent}"

RULES: PostgreSQL=$1/$2 params, MongoDB=$match/$group, apply filters/masks, max 1000 rows, use indexes.

IMPORTANT: query_type must be exactly one of: "sql", "mongodb", or "cross-db"
- Use "sql" for PostgreSQL queries (SELECT, INSERT, UPDATE, DELETE)
- Use "mongodb" for MongoDB queries (aggregation pipelines, find operations)
- Use "cross-db" only for queries spanning multiple databases

REQUIRED FIELDS:
- For MongoDB queries: MUST include "collection" field with the collection name (e.g., "users", "orders")
- For PostgreSQL queries: "collection" should be null
- "query" field: For SQL use string, for MongoDB use array of pipeline stages
- "parameters": array of parameters for SQL queries (empty array [] for MongoDB)

RETURN JSON (minimal format):
For PostgreSQL: {{"databases":["postgres"],"queries":[{{"database":"postgres","query_type":"sql","query":"SELECT * FROM table WHERE col=$1 LIMIT 1000","parameters":["val"],"estimated_rows":100,"collection":null}}]}}
For MongoDB: {{"databases":["mongodb"],"queries":[{{"database":"mongodb","query_type":"mongodb","query":[{{"$match":{{"city":"lagos"}}}},{{"$limit":1000}}],"parameters":[],"estimated_rows":100,"collection":"users"}}]}}

CRITICAL:
1. Return ONLY the JSON object, nothing else. No markdown, no explanations, no extra text before or after. Start with {{ and end with }}.
2. For MongoDB queries, the "collection" field is REQUIRED and must match a collection name from the schema.""".strip()


def build_gemini_engine(tenant: AccountConfig) -> GeminiEngine:
    """
    Build a GeminiEngine for a specific account.

    - platform mode: use global GEMINI_API_KEY
    - byo mode: use tenant.gemini_api_key
    """

    if tenant.gemini_mode == "byo":
        if not tenant.gemini_api_key:
            raise MissingBYOApiKeyError(
                "Account is configured for BYO Gemini but no API key is set")
        api_key = tenant.gemini_api_key
    else:
        api_key = settings.GEMINI_API_KEY

    return GeminiEngine(api_key=api_key, model_name=settings.GEMINI_MODEL)
