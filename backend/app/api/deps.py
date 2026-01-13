from fastapi import Header, HTTPException, status
from typing import Optional
from app.models.query import SecurityContext


async def get_security_context(
    authorization: Optional[str] = Header(None)
) -> SecurityContext:
    """
    Extract security context from request headers.
    In production, this would validate JWT tokens and extract user info.
    For demo, we'll use simple token-based auth.
    """
    
    # Demo mode - simple role extraction from header
    if not authorization:
        # Default viewer role for demo
        return SecurityContext(
            user_id=1,
            role="viewer",
            org_id=1,
            permissions=["read"],
            row_filters={},
            field_masks={}
        )
        
    # Parse "Bearer <token>" format
    if authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        
        # Demo tokens (in production, validate JWT properly)
        if token == "admin_token":
            return SecurityContext(
                user_id=1,
                role="admin",
                org_id=1,
                permissions=["read", "write", "delete"],
                row_filters={},
                field_masks={}
            )
        elif token == "viewer_token":
            return SecurityContext(
                user_id=2,
                role="viewer",
                org_id=1,
                permissions=["read"],
                row_filters={
                    "users": {"org_id": 1},
                    "orders": {"org_id": 1}
                },
                field_masks={
                    "users": ["password", "api_key"]
                }
            )
        elif token == "analyst_token":
            return SecurityContext(
                user_id=3,
                role="analyst",
                org_id=1,
                permissions=["read"],
                row_filters={},
                field_masks={
                    "users": ["password", "email", "phone"]
                }
            )
        else:
            # Allow demo_token for general testing
            return SecurityContext(
                user_id=999,
                role="demo",
                org_id=1,
                permissions=["read"],
                row_filters={},
                field_masks={}
            )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authorization header"
    )
