"""Query API endpoints"""

import logging
import traceback
import uuid

from app.api.deps import get_security_context
from app.core.accounts import (
    AccountConfig,
    get_account_by_api_key_async,
    get_account_config,
)
from app.core.demo_account import DEMO_PROJECT_API_KEY, ensure_demo_account
from app.models.query import QueryRequest, QueryResult, SecurityContext
from app.services.query_service import query_service
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResult)
async def execute_query(
    request: QueryRequest,
    security_ctx: SecurityContext = Depends(get_security_context),
    tenant: AccountConfig = Depends(get_account_config),
):
    """
    Execute a natural language database query using Gemini.

    This endpoint serves as the primary interface for running natural language queries
    against configured databases. It supports multi-tenancy through project API keys
    and includes a fallback to a demo project for easy testing.
    """

    trace_id = str(uuid.uuid4())

    # If no tenant is identified, fall back to the demo project.
    if not tenant:
        try:
            tenant = await get_account_by_api_key_async(DEMO_PROJECT_API_KEY)
        except HTTPException:
            logger.warning("Demo project not found. Attempting to create it on-demand.")
            demo_created = await ensure_demo_account()
            if demo_created:
                try:
                    tenant = await get_account_by_api_key_async(DEMO_PROJECT_API_KEY)
                    logger.info("✓ Demo project created and is now accessible.")
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
        return await query_service.execute_query(request, security_ctx, tenant)

    except ValueError as e:
        # Handle validation errors (e.g., invalid query structure).
        error_detail = str(e)
        logger.warning(f"Validation Error [{trace_id}]: {error_detail}", exc_info=True)
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
