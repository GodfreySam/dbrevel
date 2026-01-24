import logging
from typing import Optional

from app.core.config import settings
from app.models.query import SecurityContext
from fastapi import Header, HTTPException, status

logger = logging.getLogger(__name__)

# Demo tokens for testing - these are safe to use in development and testing
# In production, these tokens still work but are logged for monitoring
DEMO_TOKENS = {
    "admin_token": SecurityContext(
        user_id="user_admin",
        role="admin",
        account_id="account_admin",
        permissions=["read", "write", "delete"],
        row_filters={},
        field_masks={},
    ),
    "viewer_token": SecurityContext(
        user_id="user_viewer",
        role="viewer",
        account_id="account_demo",
        permissions=["read"],
        row_filters={
            "users": {"account_id": "account_demo"},
            "orders": {"account_id": "account_demo"},
        },
        field_masks={"users": ["password", "api_key"]},
    ),
    "analyst_token": SecurityContext(
        user_id="user_analyst",
        role="analyst",
        account_id="account_demo",
        permissions=["read"],
        row_filters={},
        field_masks={"users": ["password", "email", "phone"]},
    ),
    "demo_token": SecurityContext(
        user_id="user_demo_token",
        role="demo",
        account_id="account_demo",
        permissions=["read"],
        row_filters={},
        field_masks={},
    ),
}


async def get_security_context(
    authorization: Optional[str] = Header(None),
) -> SecurityContext:
    """
    Extract security context from request headers.

    Supports demo tokens for testing (admin_token, viewer_token, analyst_token, demo_token).
    In production, these tokens are still functional but usage is logged for monitoring.
    """
    # Demo mode - simple role extraction from header
    if not authorization:
        # Default viewer role for demo
        if not settings.DEBUG:
            logger.debug("Using default demo context (no authorization header)")
        return SecurityContext(
            user_id="user_demo",
            role="viewer",
            account_id="account_demo",
            permissions=["read"],
            row_filters={},
            field_masks={},
        )

    # Parse "Bearer <token>" format
    if authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")

        # Check if it's a demo token
        if token in DEMO_TOKENS:
            if not settings.DEBUG:
                logger.info(f"Demo token used: {token} (production mode)")
            return DEMO_TOKENS[token]

        # Unknown token - return default demo context for testing
        # In production, you might want to validate JWT here
        if not settings.DEBUG:
            logger.warning(
                f"Unknown token used (falling back to demo context): {token[:10]}..."
            )
        return SecurityContext(
            user_id="user_demo_token",
            role="demo",
            account_id="account_demo",
            permissions=["read"],
            row_filters={},
            field_masks={},
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header"
    )
