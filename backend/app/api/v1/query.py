"""Query API endpoints"""
import uuid

from app.api.deps import get_security_context
from app.core.account_store import get_account_store
from app.core.accounts import (AccountConfig, get_account_config,
                              get_account_config_required)
from app.models.query import QueryRequest, QueryResult, SecurityContext
from app.services.query_service import query_service
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()


@router.post("/query", response_model=QueryResult)
async def execute_query(
    request: QueryRequest,
    security_ctx: SecurityContext = Depends(get_security_context),
    tenant: AccountConfig = Depends(get_account_config),
):
    """
    Execute a natural language database query using Gemini 3

    ## Authentication

    This endpoint requires project identification via one of the following:

    1. **X-Project-Key Header** (Recommended for API usage):
       ```
       X-Project-Key: your_project_api_key
       ```

    2. **Demo Project** (Default for testing):
       If no header is provided, the endpoint automatically uses the demo project
       with pre-seeded sample data (ecommerce database with users, products, orders).

       Demo Project Key: `dbrevel_demo_project_key`

    ## Examples:

    **Simple Query (using demo data):**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/query" \\
      -H "Content-Type: application/json" \\
      -d '{"intent": "Get all users from Lagos"}'
    ```

    **With Project API Key:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/query" \\
      -H "Content-Type: application/json" \\
      -H "X-Project-Key: your_project_api_key" \\
      -d '{"intent": "Show total revenue by product category"}'
    ```

    **Dry Run (see query without executing):**
    ```json
    {
      "intent": "Top 5 products by price",
      "dry_run": true
    }
    ```

    ## Demo Data

    The demo project includes pre-seeded sample data:
    - **PostgreSQL**: `users`, `products`, `orders`, `order_items` tables
    - **MongoDB**: `sessions`, `reviews` collections

    Try queries like:
    - "Get all users"
    - "Show products with price over 100"
    - "Count orders by status"
    - "Get recent reviews"

    ## Response:

    Returns minimal response with:
    - **data**: Array of result rows
    - **metadata**:
      - `query_plan`: Generated queries and execution plan
      - `execution_time_ms`: Query execution time
      - `rows_returned`: Number of rows returned
      - `trace_id`: Unique trace ID for debugging
      - `timestamp`: Query execution timestamp

    ## Security:

    All queries are:
    - ✅ Validated in Gemini's sandbox
    - ✅ Checked for SQL/NoSQL injection
    - ✅ Subject to RBAC rules
    - ✅ Audited with trace IDs
    """

    trace_id = str(uuid.uuid4())

    # If no tenant provided, use demo project as fallback
    if not tenant:
        from app.core.demo_account import DEMO_PROJECT_API_KEY, ensure_demo_account
        from app.core.accounts import get_account_by_api_key_async
        import logging

        logger = logging.getLogger(__name__)

        # Look up demo project via project API key system
        try:
            demo_tenant = await get_account_by_api_key_async(DEMO_PROJECT_API_KEY)
            tenant = demo_tenant
        except HTTPException as e:
            # Demo project not found - try to create it on-demand
            logger.warning(f"⚠️  Demo project not found during query, attempting on-demand creation...")

            # Try to ensure demo tenant/project exists
            demo_created = await ensure_demo_account()

            if demo_created:
                # Try lookup again
                try:
                    demo_tenant = await get_account_by_api_key_async(DEMO_PROJECT_API_KEY)
                    tenant = demo_tenant
                    logger.info(f"✓ Demo project created on-demand and is now accessible")
                except HTTPException:
                    # Still failed - critical error
                    logger.error(f"❌ Demo project creation succeeded but lookup still fails!")
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Demo project unavailable. Please contact support or provide X-Project-Key header.",
                    )
            else:
                # Demo creation failed
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Missing API key. Demo project unavailable. Provide X-Project-Key header.",
                )

    try:
        # Delegate to QueryService, which handles full orchestration
        return await query_service.execute_query(request, security_ctx, tenant)

    except ValueError as e:
        # Validation errors (422)
        error_detail = str(e)
        print(f"VALIDATION ERROR [{trace_id}]: {error_detail}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_detail
        )
    except Exception as e:
        import traceback
        error_detail = str(e)
        error_trace = traceback.format_exc()

        # Log the full error for debugging
        print(f"ERROR [{trace_id}]: {error_detail}")
        print(f"TRACEBACK:\n{error_trace}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        )
