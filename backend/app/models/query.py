"""Query models"""
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


class QueryRequest(BaseModel):
    """Request model for natural language queries"""
    intent: str = Field(
        ...,
        description="Natural language query or structured intent",
        min_length=1,
        max_length=5000
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context")
    dry_run: bool = Field(
        default=False, description="Validate without executing")

    @field_validator('intent')
    @classmethod
    def validate_intent(cls, v: str) -> str:
        """
        Validate intent field to prevent abuse.

        NOTE: This is a basic blacklist-based protection and should be improved
        with more sophisticated prompt injection detection mechanisms.
        """
        if not v or not v.strip():
            raise ValueError("Intent cannot be empty or whitespace only")

        # Strip whitespace
        v = v.strip()

        # Check for suspicious prompt injection patterns
        suspicious_patterns = [
            "ignore all",
            "ignore previous",
            "ignore the above",
            "ignore your instructions",
            "ignore your previous instructions",
            "forget your instructions",
            "forget what you are doing",
            "do not follow your instructions",
            "disregard",
            "system:",
            "assistant:",
            "you are now",
            "you are a new assistant",
            "your new instructions are",
            "pretend you are",
        ]

        v_lower = v.lower()
        for pattern in suspicious_patterns:
            if pattern in v_lower:
                raise ValueError(
                    f"Intent contains suspicious pattern: '{pattern}'. "
                    "Please rephrase your query."
                )

        return v

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Get all users",
                    "description": "Simple query to fetch all users from the database",
                    "value": {
                        "intent": "Get all users",
                        "context": None,
                        "dry_run": False
                    }
                },
                {
                    "summary": "Get customers in Lagos with more than 5 orders",
                    "description": "Complex query with filters and aggregations",
                    "value": {
                        "intent": "Get customers in Lagos with more than 5 orders",
                        "context": None,
                        "dry_run": False
                    }
                },
                {
                    "summary": "Show products with price over 100",
                    "description": "Filter products by price threshold",
                    "value": {
                        "intent": "Show products with price over 100",
                        "context": None,
                        "dry_run": False
                    }
                },
                {
                    "summary": "Count orders by status",
                    "description": "Aggregate query to count orders grouped by status",
                    "value": {
                        "intent": "Count orders by status",
                        "context": None,
                        "dry_run": False
                    }
                },
                {
                    "summary": "Get recent reviews",
                    "description": "Query MongoDB collection for recent reviews",
                    "value": {
                        "intent": "Get recent reviews",
                        "context": None,
                        "dry_run": False
                    }
                },
                {
                    "summary": "Dry run - validate query without executing",
                    "description": "Use dry_run=true to validate query generation without executing",
                    "value": {
                        "intent": "Get all users",
                        "context": None,
                        "dry_run": True
                    }
                }
            ]
        }
    }


class DatabaseQuery(BaseModel):
    """Generated database query"""
    database: str
    query_type: Literal["sql", "mongodb", "cross-db"]
    query: Union[str, List[Dict[str, Any]]]  # SQL string or MongoDB pipeline
    parameters: Optional[List[Any]] = None
    estimated_rows: Optional[int] = None
    collection: Optional[str] = None  # For MongoDB


class QueryPlan(BaseModel):
    """Complete query execution plan (minimal)"""
    databases: List[str]
    queries: List[DatabaseQuery]
    # Removed: join_strategy, reasoning, security_applied, estimated_cost for minimal response

    model_config = {
        # Ignore extra fields from Gemini (backward compatibility)
        "extra": "ignore"
    }


class QueryMetadata(BaseModel):
    """Metadata about query execution (minimal)"""
    query_plan: QueryPlan
    execution_time_ms: float
    rows_returned: int
    trace_id: str
    timestamp: datetime
    # Removed: gemini_tokens_used, cached for minimal response


class QueryResult(BaseModel):
    """Query execution result"""
    data: List[Dict[str, Any]]
    metadata: QueryMetadata


class SecurityContext(BaseModel):
    """User security context"""
    user_id: str
    role: str
    account_id: Optional[str] = None
    permissions: List[str] = []
    row_filters: Dict[str, Dict[str, Any]] = {}
    field_masks: Dict[str, List[str]] = {}
