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


async def test_postgres_connection_lightweight(url: str, timeout: int = 30) -> ConnectionTestResult:
    """
    Test PostgreSQL connection with lightweight connectivity check.

    This function performs a fast connection test (SELECT 1) without full schema
    introspection to provide quick feedback to users. Full schema introspection
    happens during actual query execution where it's needed.

    Args:
        url: PostgreSQL connection URL
        timeout: Connection timeout in seconds (capped at 10s for faster failure)

    Returns:
        ConnectionTestResult with success status and minimal schema preview
    """
    import logging
    logger = logging.getLogger(__name__)
    adapter = None
    connect_timeout = min(timeout, 10)  # Cap at 10s for faster failure
    try:
        safe_url = url.split("@")[-1] if "@" in url else url
        logger.info(f"Testing PostgreSQL connection to: ...@{safe_url}")

        db_name = "database"
        try:
            if "/" in url:
                db_part = url.split("/")[-1].split("?")[0]
                if db_part:
                    db_name = db_part
        except Exception:
            pass

        adapter = PostgresAdapter(url)
        try:
            await asyncio.wait_for(adapter.connect(), timeout=connect_timeout)
        except asyncio.TimeoutError:
            logger.warning(
                f"PostgreSQL connection timed out after {connect_timeout}s")
            raise
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed: {str(e)}")
            raise

        try:
            async with adapter.pool.acquire() as conn:
                result = await asyncio.wait_for(conn.fetchval("SELECT 1"), timeout=10.0)
                if result != 1:
                    raise Exception("Unexpected query result")
        except asyncio.TimeoutError:
            logger.warning("PostgreSQL query test timed out")
            raise
        except Exception as e:
            logger.warning(f"PostgreSQL query test failed: {str(e)}")
            raise

        logger.info("✓ PostgreSQL connection test successful")
        schema_preview = {
            "database_name": db_name,
            "table_count": None,
            "tables": [],
        }
        await adapter.disconnect()
        return ConnectionTestResult(success=True, schema_preview=schema_preview)

    except asyncio.TimeoutError:
        if adapter:
            try:
                await adapter.disconnect()
            except Exception:
                pass
        return ConnectionTestResult(
            success=False, error="Connection timeout - database may be unreachable"
        )
    except Exception as e:
        if adapter:
            try:
                await adapter.disconnect()
            except Exception:
                pass
        error_msg = str(e)
        logger.error("PostgreSQL connection error: %s",
                     error_msg, exc_info=True)
        # Don't expose full connection details in error
        # Handle PostgreSQL connection pooler errors
        if "password" in error_msg.lower() or "authentication" in error_msg.lower():
            error_msg = "Authentication failed - check username and password"
        elif "does not exist" in error_msg.lower():
            error_msg = "Database does not exist"
        elif "refused" in error_msg.lower() or "connection" in error_msg.lower():
            error_msg = "Connection refused - check host and port"
        elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            error_msg = "Connection timeout - database may be unreachable or pooler is busy"
        elif "pool" in error_msg.lower() or "pooler" in error_msg.lower():
            error_msg = "Connection pool error - try again in a moment"

        return ConnectionTestResult(success=False, error=error_msg)


async def test_postgres_connection(url: str, timeout: int = 30) -> ConnectionTestResult:
    """
    Test PostgreSQL connection (backward compatibility wrapper).

    This function calls the lightweight test for backward compatibility.
    For fast connection testing, use test_postgres_connection_lightweight() directly.

    Args:
        url: PostgreSQL connection URL
        timeout: Connection timeout in seconds

    Returns:
        ConnectionTestResult with success status and minimal schema preview
    """
    return await test_postgres_connection_lightweight(url, timeout)


async def test_mongodb_connection_lightweight(url: str, timeout: int = 10) -> ConnectionTestResult:
    """
    Test MongoDB connection with lightweight connectivity check.

    This function performs a fast connection test (ping) without full schema
    introspection to provide quick feedback to users. Full schema introspection
    happens during actual query execution where it's needed.

    Args:
        url: MongoDB connection URL
        timeout: Connection timeout in seconds

    Returns:
        ConnectionTestResult with success status and minimal schema preview
    """
    adapter = None
    try:
        # Extract database name from URL
        db_name = url.split("/")[-1].split("?")[0]
        if not db_name:
            db_name = "test"

        import logging
        logger = logging.getLogger(__name__)
        logger.info("Testing MongoDB connection (lightweight)")

        adapter = MongoDBAdapter(url, db_name)
        await asyncio.wait_for(adapter.connect(), timeout=timeout)

        # Test connection with ping (lightweight check)
        await adapter.health_check()

        # Return minimal schema preview (no introspection)
        schema_preview = {
            "database_name": db_name,
            "collection_count": None,  # Not counted in lightweight test
            "collections": [],
        }

        await adapter.disconnect()
        return ConnectionTestResult(success=True, schema_preview=schema_preview)

    except asyncio.TimeoutError:
        if adapter:
            try:
                await adapter.disconnect()
            except Exception:
                pass
        return ConnectionTestResult(
            success=False, error="Connection timeout - database may be unreachable"
        )
    except Exception as e:
        if adapter:
            try:
                await adapter.disconnect()
            except Exception:
                pass
        error_msg = str(e)
        import logging
        logging.error(
            f"MongoDB connection error for URL {url}: {error_msg}", exc_info=True)
        # Sanitize error messages
        if "authentication" in error_msg.lower():
            error_msg = "Authentication failed - check username and password"
        elif "refused" in error_msg.lower() or "connection" in error_msg.lower():
            error_msg = "Connection refused - check host and port"
        elif "not authorized" in error_msg.lower():
            error_msg = "Not authorized - check database permissions"

        return ConnectionTestResult(success=False, error=error_msg)


async def test_mongodb_connection(url: str, timeout: int = 10) -> ConnectionTestResult:
    """
    Test MongoDB connection and return schema preview (full introspection).

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
        collections_list_items = list(
            schema.collections.items()) if schema.collections else []
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
            except Exception:
                pass
        return ConnectionTestResult(
            success=False, error="Connection timeout - database may be unreachable"
        )
    except Exception as e:
        if adapter:
            try:
                await adapter.disconnect()
            except Exception:
                pass
        error_msg = str(e)
        import logging
        logging.error(
            f"MongoDB connection error for URL {url}: {error_msg}", exc_info=True)
        # Sanitize error messages
        if "authentication" in error_msg.lower():
            error_msg = "Authentication failed - check username and password"
        elif "refused" in error_msg.lower() or "connection" in error_msg.lower():
            error_msg = "Connection refused - check host and port"
        elif "not authorized" in error_msg.lower():
            error_msg = "Not authorized - check database permissions"

        return ConnectionTestResult(success=False, error=error_msg)
