"""Base database adapter interface"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from app.models.schema import DatabaseSchema


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters"""

    @abstractmethod
    async def connect(self) -> None:
        """Establish database connection"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close database connection"""
        pass

    @abstractmethod
    async def introspect_schema(self) -> DatabaseSchema:
        """Introspect and return database schema"""
        pass

    @abstractmethod
    async def execute(
        self, query: Any, params: List[Any] = None
    ) -> List[Dict[str, Any]]:
        """Execute query and return results"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if database is healthy"""
        pass
