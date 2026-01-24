"""Rate limiting middleware for API endpoints"""
import logging
import os
from typing import Optional

from app.core.config import settings
from fastapi import Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Disable rate limiting in test mode
is_testing = os.getenv("TESTING", "false").lower() == "true"

# Initialize rate limiter
# Use Redis if available, otherwise fall back to in-memory storage
if is_testing:
    # Disable rate limiting in test mode
    limiter = None
    logger.info("Rate limiting disabled (TESTING mode)")
else:
    try:
        if settings.REDIS_URL:
            # Use Redis backend for distributed rate limiting
            limiter = Limiter(
                key_func=get_remote_address,
                storage_uri=settings.REDIS_URL,
                default_limits=["1000/hour"],  # Default limit if not specified
            )
            logger.info("Rate limiting using Redis backend")
        else:
            # Use in-memory backend (single instance only)
            limiter = Limiter(
                key_func=get_remote_address,
                default_limits=["1000/hour"],
            )
            logger.info(
                "Rate limiting using in-memory backend (Redis not configured)")
    except Exception as e:
        logger.warning(
            f"Failed to initialize rate limiter: {e}. Rate limiting disabled.")
        limiter = None


def get_api_key_for_rate_limit(request: Request) -> Optional[str]:
    """
    Extract API key from request headers for per-key rate limiting.
    Falls back to IP address if no API key is present.
    """
    # Try to get API key from X-Project-Key header
    api_key = request.headers.get("X-Project-Key")
    if api_key:
        return f"api_key:{api_key}"

    # Fall back to IP address
    return get_remote_address(request)


# Rate limit decorators for different endpoint types
def rate_limit_auth():
    """Rate limit for authentication endpoints (login, register, etc.)"""
    if limiter is None:
        return lambda f: f  # No-op if limiter not initialized
    return limiter.limit("5/minute", key_func=get_remote_address)


def rate_limit_query():
    """Rate limit for query endpoints (more restrictive due to AI costs)"""
    if limiter is None:
        return lambda f: f  # No-op if limiter not initialized
    # Use API key if available, otherwise IP address
    return limiter.limit("30/minute", key_func=get_api_key_for_rate_limit)


def rate_limit_general():
    """Rate limit for general API endpoints"""
    if limiter is None:
        return lambda f: f  # No-op if limiter not initialized
    return limiter.limit("100/minute", key_func=get_remote_address)


def rate_limit_strict():
    """Rate limit for sensitive operations (password reset, etc.)"""
    if limiter is None:
        return lambda f: f  # No-op if limiter not initialized
    return limiter.limit("3/minute", key_func=get_remote_address)
