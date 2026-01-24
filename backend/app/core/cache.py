"""Redis-based cache for schemas and query plans, replacing the simple in-memory cache."""

import hashlib
import logging
import orjson
import redis
from typing import Any, Optional, Union

from app.core.config import settings

logger = logging.getLogger(__name__)

# Type alias for Redis client (can be real Redis or MockRedis)
RedisClient = Union[redis.Redis[str], Any]


# A simple mock client that does nothing, to avoid errors
class MockRedis:
    def get(self, name: str) -> None:
        return None

    def set(self, name: str, value: Any, ex: Optional[int] = None) -> None:
        pass

    def flushdb(self) -> None:
        pass

    def ping(self) -> None:
        raise redis.exceptions.ConnectionError

    def scan_iter(self, match: str) -> list:
        return []

    def delete(self, key: str) -> None:
        pass


# Initialize Redis client from the URL in settings
# The client will be shared across the application
try:
    # Adding decode_responses=True to handle strings automatically
    redis_client: RedisClient = redis.from_url(settings.REDIS_URL, decode_responses=True)
    # Check if the connection is alive
    redis_client.ping()
except redis.exceptions.ConnectionError:
    # If Redis is not available, use a mock client (Redis is optional)
    # Only log at debug level since Redis is optional for local dev
    logger.debug(
        "Redis not available - caching will be disabled (this is OK for local development)"
    )
    redis_client = MockRedis()
except Exception as e:
    # Unexpected errors - log at info level but don't fail
    logger.info(
        f"Redis initialization issue: {type(e).__name__}. Caching will be disabled."
    )
    redis_client = MockRedis()


class RedisCache:
    """Redis-based cache with TTL and automatic serialization."""

    def __init__(self, client, prefix: str = "cache"):
        self.client = client
        self.prefix = prefix

    def _get_key(self, key: str) -> str:
        """Applies a prefix to the key to avoid collisions in Redis."""
        return f"{self.prefix}:{key}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis cache and deserialize it."""
        try:
            cached_value = self.client.get(self._get_key(key))
            if cached_value is None:
                return None
            # Deserialize using orjson, which is faster than standard json
            return orjson.loads(cached_value)
        except (redis.exceptions.RedisError, orjson.JSONDecodeError) as e:
            logger.debug(f"Redis cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Serialize value and set it in Redis cache with a TTL."""
        try:
            # Default function to handle objects that orjson can't serialize
            # This is particularly useful for Pydantic models
            def default_serializer(obj):
                if hasattr(obj, "model_dump"):
                    return obj.model_dump()
                return str(obj)

            # Serialize using orjson with the default serializer
            serialized_value = orjson.dumps(value, default=default_serializer)
            self.client.set(self._get_key(key), serialized_value, ex=ttl_seconds)
        except redis.exceptions.RedisError as e:
            logger.debug(f"Redis cache set error: {e}")

    def clear(self):
        """Clear all cache entries managed by this instance (by prefix).
        This is safer than flushdb if Redis is shared.
        """
        try:
            # Using scan to avoid blocking the server with a large number of keys
            for key in self.client.scan_iter(f"{self.prefix}:*"):
                self.client.delete(key)
        except redis.exceptions.RedisError as e:
            logger.debug(f"Redis cache clear error: {e}")

    def generate_key(self, *args, **kwargs) -> str:
        """Generate a consistent cache key from arguments."""

        # Use orjson for fast and consistent serialization
        # The default function ensures complex objects are handled
        def default_serializer(obj):
            if hasattr(obj, "model_dump"):
                return obj.model_dump(mode="json")
            return str(obj)

        # Combine args and kwargs for a complete key
        key_data = {"args": args, "kwargs": kwargs}
        key_str = orjson.dumps(
            key_data, default=default_serializer, option=orjson.OPT_SORT_KEYS
        )
        return hashlib.md5(key_str).hexdigest()


# Global cache instances using the Redis-based cache
# Using different prefixes for schema and query plans
schema_cache = RedisCache(redis_client, prefix="schema")
query_plan_cache = RedisCache(redis_client, prefix="query_plan")
