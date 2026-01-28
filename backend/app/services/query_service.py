import asyncio
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List

from app.adapters.factory import adapter_factory
from app.core.exceptions import (
    InvalidQueryError,
    MissingCollectionError,
    QueryValidationError,
    UnsupportedQueryError,
)
from app.core.gemini import build_gemini_engine
from app.core.usage import record_usage
from app.models.query import (
    QueryMetadata,
    QueryPlan,
    QueryRequest,
    QueryResult,
    SecurityContext,
)


class QueryService:
    """Main query orchestration service"""

    async def execute_query(
        self,
        request: QueryRequest,
        security_ctx: SecurityContext,
        tenant,
    ) -> QueryResult:
        """Execute natural language query with full orchestration (explanation-free)"""

        trace_id = str(uuid.uuid4())
        start_time = time.time()

        try:
            # 1. Get all database schemas for this tenant
            schemas = await adapter_factory.get_all_schemas(tenant)

            # 2. Generate query plan using Gemini
            gemini_engine = build_gemini_engine(tenant)
            plan = await gemini_engine.generate_query_plan(
                intent=request.intent, schemas=schemas, security_ctx=security_ctx
            )

            # 3. Dry run mode - just return the plan (no execution)
            if request.dry_run:
                return self._build_dry_run_response(plan, trace_id)

            # 4. Validate queries with Gemini (optional for production optimization)
            if not request.skip_validation:
                for query in plan.queries:
                    schema = schemas[query.database]
                    validation = await gemini_engine.validate_query(query, schema)

                    if not validation.get("safe", True):
                        raise QueryValidationError(
                            f"Unsafe query detected: {validation.get('issues', [])}"
                        )
            else:
                # Log when validation is skipped for monitoring
                print(
                    f"[VALIDATION_SKIPPED] trace={trace_id} intent={request.intent[:100]}"
                )

            # 5. Execute queries
            if len(plan.queries) == 1:
                # Single database query
                results = await self._execute_single_db(plan, tenant)
            else:
                # Cross-database query
                results = await self._execute_cross_db(plan, tenant)

            # 6. Apply security post-processing (field masking)
            secured_results = self._apply_field_masking(results, security_ctx)

            # 7. Build response
            execution_time = (time.time() - start_time) * 1000

            metadata = QueryMetadata(
                query_plan=plan,
                execution_time_ms=execution_time,
                rows_returned=len(secured_results),
                trace_id=trace_id,
                timestamp=datetime.now(),
            )

            # 8. Record basic per-account usage
            record_usage(
                account_id=getattr(tenant, "id", "unknown"),
                trace_id=trace_id,
                execution_time_ms=execution_time,
                gemini_tokens_used=0,  # Tracked separately if needed
            )

            result = QueryResult(
                data=secured_results,
                metadata=metadata,
            )

            return result

        except Exception as e:
            print(f"Query execution error [{trace_id}]: {e}")
            raise

    async def _execute_single_db(self, plan: QueryPlan, tenant) -> List[Dict[str, Any]]:
        """Execute query against single database"""

        query_obj = plan.queries[0]
        # Resolve adapter for this account and database
        adapter = await adapter_factory.get(account=tenant, name=query_obj.database)

        # Execute based on query type
        if query_obj.query_type == "sql":
            results = await adapter.execute(query_obj.query, query_obj.parameters)
        elif query_obj.query_type == "mongodb":
            # MongoDB queries must have a collection specified
            if not isinstance(query_obj.query, list):
                raise InvalidQueryError(
                    "Invalid MongoDB query format: query must be a list (pipeline)"
                )

            # Use collection from query plan, or try to infer from schema
            collection = query_obj.collection
            if not collection:
                raise MissingCollectionError(
                    "Collection name required for MongoDB queries. The query plan must include a 'collection' field."
                )

            results = await adapter.execute(
                query_obj.query, [collection] if collection else None
            )
        else:
            raise UnsupportedQueryError(
                f"Unsupported query type: {query_obj.query_type}"
            )

        return results

    async def _execute_cross_db(self, plan: QueryPlan, tenant) -> List[Dict[str, Any]]:
        """Execute and join queries across multiple databases"""

        # Execute all queries in parallel
        tasks = []
        for query_obj in plan.queries:
            adapter = await adapter_factory.get(account=tenant, name=query_obj.database)

            if query_obj.query_type == "sql":
                task = adapter.execute(query_obj.query, query_obj.parameters)
            elif query_obj.query_type == "mongodb":
                # MongoDB queries require collection name
                if not query_obj.collection:
                    raise MissingCollectionError(
                        f"Collection name required for MongoDB query on database '{query_obj.database}'"
                    )
                task = adapter.execute(
                    query_obj.query,
                    [query_obj.collection] if query_obj.collection else None,
                )
            else:
                raise UnsupportedQueryError(
                    f"Unsupported query type for cross-db query: {query_obj.query_type}"
                )

            tasks.append(task)

        results_list = await asyncio.gather(*tasks)

        # Simple merge strategy: concatenate all results
        # Note: For production, consider implementing proper join strategies:
        # - hash_join: For large datasets with equality joins
        # - nested_loop: For small datasets or complex conditions
        # - merge_join: For sorted datasets
        # Current implementation uses simple concatenation which works for UNION-like queries
        merged = []
        for result_set in results_list:
            merged.extend(result_set)

        return merged

    def _apply_field_masking(
        self, results: List[Dict[str, Any]], security_ctx: SecurityContext
    ) -> List[Dict[str, Any]]:
        """Apply field-level masking based on security context"""

        if not security_ctx.field_masks:
            return results

        masked_results = []
        for row in results:
            masked_row = row.copy()

            # Apply masks from security context
            for table, fields in security_ctx.field_masks.items():
                for field in fields:
                    if field in masked_row:
                        masked_row[field] = "***MASKED***"

            masked_results.append(masked_row)

        return masked_results

    def _build_dry_run_response(self, plan: QueryPlan, trace_id: str) -> QueryResult:
        """Build response for dry-run mode"""

        metadata = QueryMetadata(
            query_plan=plan,
            execution_time_ms=0,
            rows_returned=0,
            trace_id=trace_id,
            timestamp=datetime.now(),
        )

        return QueryResult(
            data=[],
            metadata=metadata,
        )


# Singleton instance
query_service = QueryService()
