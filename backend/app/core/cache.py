"""Simple in-memory cache for schemas and query plans"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


class SimpleCache:
    """Thread-safe in-memory cache with TTL"""

    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if datetime.now() > entry['expires_at']:
            del self._cache[key]
            return None

        # Deserialize if it's a dict (Pydantic model)
        value = entry['value']
        if isinstance(value, dict) and '_pydantic_model' in str(type(value)):
            # Return as-is for Pydantic models (they're already objects)
            return value
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 3600):
        """Set value in cache with TTL"""
        # Pydantic models can be stored directly
        self._cache[key] = {
            'value': value,
            'expires_at': datetime.now() + timedelta(seconds=ttl_seconds)
        }

    def clear(self):
        """Clear all cache entries"""
        self._cache.clear()

    def generate_key(self, *args) -> str:
        """Generate cache key from arguments"""
        key_str = json.dumps(args, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()


# Global cache instances
schema_cache = SimpleCache()
query_plan_cache = SimpleCache()
