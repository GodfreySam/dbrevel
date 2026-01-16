"""Database connection testing utilities."""

import asyncio
from typing import Any, Dict, Optional

from app.adapters.mongodb import MongoDBAdapter
from app.adapters.postgres import PostgresAdapter


class ConnectionTestResult:
    """Result of a database connection test."""

    def __init__(
        self,
        success: bool,
        error: Optional[str] = None,
        schema_preview: Optional[Dict[str, Any]] = None,
    ):
        self.success = success
        self.error = error
        self.schema_preview = schema_preview

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "success": self.success,
            "error": self.error,
            "schema_preview": self.schema_preview,
        }


async def test_postgres_connection(url: str, timeout: int = 10) -> ConnectionTestResult:
    """
    Test PostgreSQL connection and return schema preview.

    Args:
        url: PostgreSQL connection URL
        timeout: Connection timeout in seconds

    Returns:
        ConnectionTestResult with success status and schema preview
    """
    adapter = None
    try:
        adapter = PostgresAdapter(url)
        await asyncio.wait_for(adapter.connect(), timeout=timeout)

        # Introspect schema
        schema = await adapter.introspect_schema()

        # Create schema preview (first few tables with column counts)
        # Ensure tables is a list before slicing
        tables_list = list(schema.tables.values()) if schema.tables else []
        schema_preview = {
            "database_name": schema.name,
            "table_count": len(tables_list),
            "tables": [
                {
                    "name": table.name,
                    "column_count": len(table.columns) if table.columns else 0,
                    # First 5 columns - ensure columns is a list
                    "columns": [col.name for col in (list(table.columns)[:5] if table.columns else [])],
                }
                # First 10 tables
                for table in tables_list[:10]
            ],
        }

        await adapter.disconnect()
        return ConnectionTestResult(success=True, schema_preview=schema_preview)

    except asyncio.TimeoutError:
        if adapter:
            try:
                await adapter.disconnect()
            except:
                pass
        return ConnectionTestResult(
            success=False, error="Connection timeout - database may be unreachable"
        )
    except Exception as e:
        if adapter:
            try:
                await adapter.disconnect()
            except:
                pass
        error_msg = str(e)
        import logging
        logging.error(f"PostgreSQL connection error: {error_msg}", exc_info=True)
        # Don't expose full connection details in error
        if "password" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Authentication failed - check username and password"
        elif "does not exist" in error_msg.lower():
            error_msg = "Database does not exist"
        elif "refused" in error_msg.lower() or "connection" in error_msg.lower():
            error_msg = "Connection refused - check host and port"

        return ConnectionTestResult(success=False, error=error_msg)


async def test_mongodb_connection(url: str, timeout: int = 10) -> ConnectionTestResult:
    """
    Test MongoDB connection and return schema preview.

    Args:
        url: MongoDB connection URL
        timeout: Connection timeout in seconds

    Returns:
        ConnectionTestResult with success status and schema preview
    """
    adapter = None
    try:
        # Extract database name from URL
        db_name = url.split("/")[-1].split("?")[0]
        if not db_name:
            db_name = "test"

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Attempting MongoDB connection test with URL: {url}")

        adapter = MongoDBAdapter(url, db_name)
        await asyncio.wait_for(adapter.connect(), timeout=timeout)

        # Test connection with ping
        await adapter.health_check()

        # Introspect schema
        schema = await adapter.introspect_schema()

        # Create schema preview
        # Ensure collections is a list before slicing
        collections_list_items = list(schema.collections.items()) if schema.collections else []
        schema_preview = {
            "database_name": schema.name,
            "collection_count": len(collections_list_items),
            "collections": [
                {
                    "name": coll_name,
                    "field_count": len(coll_dict.get("fields", {})),
                    # First 5 fields
                    "fields": list(coll_dict.get("fields", {}).keys())[:5],
                }
                for coll_name, coll_dict in collections_list_items[:10]
            ],
        }

        await adapter.disconnect()
        return ConnectionTestResult(success=True, schema_preview=schema_preview)

    except asyncio.TimeoutError:
        if adapter:
            try:
                await adapter.disconnect()
            except:
                pass
        return ConnectionTestResult(
            success=False, error="Connection timeout - database may be unreachable"
        )
    except Exception as e:
        if adapter:
            try:
                await adapter.disconnect()
            except:
                pass
        error_msg = str(e)
        import logging
        logging.error(f"MongoDB connection error for URL {url}: {error_msg}", exc_info=True)
        # Sanitize error messages
        if "authentication" in error_msg.lower():
            error_msg = "Authentication failed - check username and password"
        elif "refused" in error_msg.lower() or "connection" in error_msg.lower():
            error_msg = "Connection refused - check host and port"
        elif "not authorized" in error_msg.lower():
            error_msg = "Not authorized - check database permissions"

        return ConnectionTestResult(success=False, error=error_msg)

