"""Authentication utilities for password hashing and JWT tokens."""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from app.core.config import settings
from app.models.user import User
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

# JWT security scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Since bcrypt has a 72-byte limit, we first hash long passwords with SHA256
    to ensure we stay within the limit while supporting passwords of any length.

    This approach:
    - Passwords <= 72 bytes: hashed directly with bcrypt
    - Passwords > 72 bytes: SHA256 hashed first (produces 32 bytes), then bcrypt

    Args:
        password: Plain text password

    Returns:
        Hashed password string (bcrypt hash)
    """
    password_bytes = password.encode('utf-8')

    # If password is longer than 72 bytes, pre-hash with SHA256
    if len(password_bytes) > 72:
        # Hash with SHA256 first (produces exactly 32 bytes)
        sha256_hash = hashlib.sha256(password_bytes).digest()
        # Convert to hex string (64 bytes, still under 72 limit) for bcrypt
        password_to_hash = sha256_hash.hex()
    else:
        password_to_hash = password

    # Use bcrypt directly (avoid passlib compatibility issues)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_to_hash.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Handles both directly hashed passwords and SHA256-pre-hashed passwords
    for compatibility with the hash_password function.

    Also supports legacy passlib hashes for backward compatibility.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored password hash (bcrypt hash string)

    Returns:
        True if password matches, False otherwise
    """
    # Prepare password the same way as hash_password
    password_bytes = plain_password.encode('utf-8')

    # If password is longer than 72 bytes, pre-hash with SHA256
    if len(password_bytes) > 72:
        sha256_hash = hashlib.sha256(password_bytes).digest()
        password_to_verify = sha256_hash.hex()
    else:
        password_to_verify = plain_password

    # Use bcrypt directly to verify (bcrypt hashes are compatible between direct bcrypt and passlib)
    try:
        password_byte = password_to_verify.encode('utf-8')
        hashed_password_byte = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_byte, hashed_password_byte)
    except (ValueError, TypeError, AttributeError, UnicodeEncodeError):
        # If direct bcrypt fails, try passlib as fallback (for edge cases or legacy hashes)
        try:
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            # Try with original password first (for legacy hashes without pre-hashing)
            if pwd_context.verify(plain_password, hashed_password):
                return True
            # Try with pre-hashed password (for new hashes)
            return pwd_context.verify(password_to_verify, hashed_password)
        except Exception:
            return False
    except Exception:
        return False


def create_access_token(user_id: str, email: str, role: str = "user") -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to encode in token
        email: User email to encode in token
        role: User role ("user" or "admin")

    Returns:
        Encoded JWT token string
    """
    expire = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    ),
) -> Optional[User]:
    """
    Optional JWT authentication - returns None if no token provided.
    Used for endpoints that support both JWT and API key auth.
    """
    if not credentials:
        return None

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        return None

    user_id: str = payload.get("sub")
    if user_id is None:
        return None

    # Get user from database
    import app.core.user_store as user_store_module
    user_store = user_store_module.user_store
    if user_store is None:
        return None
    user = await user_store.get_by_id(user_id)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    FastAPI dependency to get current authenticated user from JWT token.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User object if token is valid

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    import app.core.user_store as user_store_module
    user_store = user_store_module.user_store
    if user_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized. Please restart the server.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Log token info for debugging (without exposing full token)
    token_preview = f"{token[:10]}...{token[-10:]}" if len(token) > 20 else "***"
    logging.debug(f"get_current_user: Validating token for user_id={user_id} (token: {token_preview})")

    user = await user_store.get_by_id(user_id)

    if user is None:
        logging.error(f"get_current_user: User not found for user_id={user_id} from token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logging.debug(
        f"get_current_user: Retrieved user {user.email} (id={user.id}, "
        f"email_verified={user.email_verified}, tenant_id={user.tenant_id})"
    )

    # Check if email is verified
    if not user.email_verified:
        logging.warning(
            f"get_current_user: User {user.email} (id={user.id}, tenant_id={user.tenant_id}) "
            f"attempted to access protected resource but email is not verified "
            f"(email_verified={user.email_verified}). User should verify email before accessing protected endpoints."
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Email not verified. User ID: {user.id}, Email: {user.email}. "
                f"Please check your email and verify your account before accessing protected resources. "
                f"Use /api/v1/auth/verify-email endpoint to verify your email address."
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """
    FastAPI dependency for admin-only endpoints.

    Verifies JWT token and checks that user has admin role.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        User object if token is valid and user is admin

    Raises:
        HTTPException: If token is invalid, user not found, or user is not admin
    """
    # First verify the user is authenticated
    user = await get_current_user(credentials)

    # Check if user has admin role
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user
