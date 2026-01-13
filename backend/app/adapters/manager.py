"""Adapter manager for database connections"""
from typing import Dict, Optional

from app.adapters.base import DatabaseAdapter

# Global database adapters
postgres_adapter: Optional[DatabaseAdapter] = None
mongodb_adapter: Optional[DatabaseAdapter] = None


def get_adapters() -> Dict[str, Optional[DatabaseAdapter]]:
    """Get all database adapters"""
    return {
        "postgres": postgres_adapter,
        "mongodb": mongodb_adapter
    }


def set_postgres_adapter(adapter: DatabaseAdapter):
    """Set the PostgreSQL adapter"""
    global postgres_adapter
    postgres_adapter = adapter


def set_mongodb_adapter(adapter: DatabaseAdapter):
    """Set the MongoDB adapter"""
    global mongodb_adapter
    mongodb_adapter = adapter
