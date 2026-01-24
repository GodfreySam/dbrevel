"""Query API endpoints"""

import logging
import traceback
import uuid

from app.api.deps import get_security_context
from app.core.accounts import (AccountConfig, get_account_by_api_key_async,
                               get_account_config)
from app.core.demo_account import DEMO_PROJECT_API_KEY, ensure_demo_account
from app.core.rate_limit import rate_limit_query
from app.models.query import QueryRequest, QueryResult, SecurityContext
from app.services.query_service import query_service
from fastapi import (APIRouter, Body, Depends, HTTPException, Request,
                     status)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/query",
    response_model=QueryResult,
    summary="Execute Natural Language Query",
    description="""
Execute a natural language database query using Gemini AI.

**How to use:**
1. **With Demo Project (Recommended for testing):**
   - Leave `X-Project-Key` header empty or use: `dbrevel_demo_project_key`
   - Demo project includes pre-seeded sample data (users, products, orders, reviews)
   - No authentication required - perfect for trying out the API!

2. **With Your Own Project:**
   - Set `X-Project-Key` header to your project's API key
   - Get your API key from the dashboard after creating a project

**Example Queries:**
- "Get all users"
- "Show products with price over 100"
- "Count orders by status"
- "Get customers in Lagos with more than 5 orders"
- "Get recent reviews"

**Demo Data Available:**
- **PostgreSQL**: `users`, `products`, `orders`, `order_items` tables
- **MongoDB**: `sessions`, `reviews` collections

**Try it out:** Click "Try it out" below, select an example query, and click "Execute"!
    """,
    responses={
        200: {
            "description": "Query executed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {"id": 1, "name": "John Doe",
                                "email": "john@example.com"},
                            {"id": 2, "name": "Jane Smith",
                                "email": "jane@example.com"}
                        ],
                        "metadata": {
                            "rows_returned": 2,
                            "execution_time_ms": 234.5,
                            "trace_id": "550e8400-e29b-41d4-a716-446655440000",
                            "timestamp": "2024-01-15T10:30:00Z",
                            "query_plan": {
                                "databases": ["postgres"],
                                "queries": [
                                    {
                                        "database": "postgres",
                                        "query_type": "sql",
                                        "query": "SELECT * FROM users LIMIT 1000",
                                        "parameters": [],
                                        "estimated_rows": 2
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        },
        401: {
            "description": "Unauthorized - Invalid or missing API key",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Missing X-Project-Key header. The demo project is also unavailable."
                    }
                }
            }
        },
        422: {
            "description": "Validation error - Invalid query intent",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Intent cannot be empty or whitespace only"
                    }
                }
            }
        }
    }
)
@rate_limit_query()
async def execute_query(
    request: Request,
    request_body: QueryRequest = Body(
        ...,
        examples={
            "simple_query": {
                "summary": "Get all users",
                "description": "Simple query to fetch all users from the database",
                "value": {
                    "intent": "Get all users",
                    "context": None,
                    "dry_run": False
                }
            },
            "complex_query": {
                "summary": "Get customers in Lagos with more than 5 orders",
                "description": "Complex query with filters and aggregations",
                "value": {
                    "intent": "Get customers in Lagos with more than 5 orders",
                    "context": None,
                    "dry_run": False
                }
            },
            "filter_query": {
                "summary": "Show products with price over 100",
                "description": "Filter products by price threshold",
                "value": {
                    "intent": "Show products with price over 100",
                    "context": None,
                    "dry_run": False
                }
            },
            "aggregate_query": {
                "summary": "Count orders by status",
                "description": "Aggregate query to count orders grouped by status",
                "value": {
                    "intent": "Count orders by status",
                    "context": None,
                    "dry_run": False
                }
            },
            "mongodb_query": {
                "summary": "Get recent reviews",
                "description": "Query MongoDB collection for recent reviews",
                "value": {
                    "intent": "Get recent reviews",
                    "context": None,
                    "dry_run": False
                }
            },
            "dry_run": {
                "summary": "Dry run - validate query without executing",
                "description": "Use dry_run=true to validate query generation without executing",
                "value": {
                    "intent": "Get all users",
                    "context": None,
                    "dry_run": True
                }
            }
        }
    ),
    security_ctx: SecurityContext = Depends(get_security_context),
    tenant: AccountConfig = Depends(get_account_config),
):

    trace_id = str(uuid.uuid4())

    # Log request for debugging validation issues
    logger.debug(
        f"Query request received [{trace_id}]: intent='{request_body.intent}', dry_run={request_body.dry_run}")

    # If no tenant is identified, fall back to the demo project.
    if not tenant:
        try:
            tenant = await get_account_by_api_key_async(DEMO_PROJECT_API_KEY)
        except HTTPException:
            logger.warning(
                "Demo project not found. Attempting to create it on-demand.")
            demo_created = await ensure_demo_account()
            if demo_created:
                try:
                    tenant = await get_account_by_api_key_async(DEMO_PROJECT_API_KEY)
                    logger.info(
                        "✓ Demo project created and is now accessible.")
                except HTTPException:
                    logger.error(
                        "❌ Demo project creation succeeded, but lookup still fails."
                    )
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Demo project is temporarily unavailable. Please try again shortly.",
                    )
            else:
                logger.error("❌ Failed to create the demo project on-demand.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Project-Key header. The demo project is also unavailable.",
            )

    try:
        # Delegate to the QueryService for full orchestration.
        return await query_service.execute_query(request_body, security_ctx, tenant)

    except ValueError as e:
        # Handle validation errors (e.g., invalid query structure).
        error_detail = str(e)
        logger.warning(
            f"Validation Error [{trace_id}]: {error_detail}. Request body: intent='{request_body.intent}', context={request_body.context}, dry_run={request_body.dry_run}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error_detail
        )
    except Exception as e:
        # Catch-all for unexpected server errors.
        error_detail = str(e)
        error_trace = traceback.format_exc()
        logger.error(
            f"Internal Server Error [{trace_id}]: {error_detail}\n{error_trace}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_detail
        )
