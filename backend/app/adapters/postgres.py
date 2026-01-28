"""
This module provides a PostgreSQL database adapter for the application.

It includes the `PostgresAdapter` class, which implements the `DatabaseAdapter` interface
for connecting to and interacting with a PostgreSQL database. The adapter uses the `asyncpg`
library for asynchronous database operations and includes features like connection pooling,
schema introspection with retry logic, and query execution with result size limits.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import asyncpg  # type: ignore[import-untyped]
from app.adapters.base import DatabaseAdapter
from app.core.config import settings
from app.core.retry import with_retry
from app.models.schema import ColumnSchema, DatabaseSchema, TableSchema
from asyncpg.exceptions import \
    ConnectionDoesNotExistError  # type: ignore[import-untyped]


class PostgresAdapter(DatabaseAdapter):
    """
    PostgreSQL database adapter.

    This class manages a connection pool to a PostgreSQL database and provides
    methods for schema introspection and query execution. It is designed to be
    resilient to transient connection errors using a retry mechanism.
    """

    def __init__(self, connection_string: str):
        """
        Initializes the PostgresAdapter.

        Args:
            connection_string: The connection string for the PostgreSQL database.
        """
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
        self._schema: Optional[DatabaseSchema] = None

    async def connect(self) -> None:
        """
        Creates and establishes the connection pool to the database.

        Configures the pool for compatibility with connection poolers (Neon, Supabase, etc.)
        by disabling the statement cache. Validates connections on actual use.
        """
        import logging

        logger = logging.getLogger(__name__)
        try:
            self.pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=settings.POSTGRES_POOL_MIN_SIZE,
                max_size=settings.POSTGRES_POOL_MAX_SIZE,
                command_timeout=60,
                timeout=10,
                statement_cache_size=0,
                max_inactive_connection_lifetime=45,
            )
            logger.debug(
                f"PostgreSQL connection pool created (min={settings.POSTGRES_POOL_MIN_SIZE}, max={settings.POSTGRES_POOL_MAX_SIZE})"
            )
        except (asyncio.TimeoutError, TimeoutError) as e:
            # Timeout errors are common during startup/pre-warming - log as warning
            logger.warning(
                "PostgreSQL connection pool creation timed out (will retry on-demand): %s",
                e,
            )
            raise
        except Exception as e:
            logger.error(
                "Failed to create PostgreSQL connection pool: %s", e, exc_info=True
            )
            raise

    async def disconnect(self) -> None:
        """Closes the connection pool and terminates all database connections."""
        if self.pool:
            try:
                # Close the pool with timeout to prevent hanging
                await asyncio.wait_for(self.pool.close(), timeout=2.0)
                self.pool = None
            except asyncio.TimeoutError:
                logging.getLogger(__name__).warning(
                    "PostgreSQL pool close timed out, forcing close"
                )
                self.pool = None
            except Exception as e:
                logging.getLogger(__name__).warning(
                    f"Error closing PostgreSQL pool: {e}"
                )
                self.pool = None

    async def _reconnect_pool(self) -> None:
        """Close the pool and create a new one. Use after ConnectionDoesNotExistError so retries get fresh connections."""
        if self.pool:
            await self.pool.close()
            self.pool = None
        await self.connect()

    @with_retry(exceptions=(ConnectionDoesNotExistError,), max_retries=3)
    async def introspect_schema(self) -> DatabaseSchema:
        """
        Introspects the PostgreSQL database schema and returns a structured representation.

        This method fetches metadata about tables, columns, primary keys, and foreign keys
        for the 'public' schema. It also attempts to get the row count for each table.
        The result is cached to avoid redundant introspection.

        Returns:
            A `DatabaseSchema` object representing the database structure.
        """
        if self._schema:
            return self._schema

        meta_query = """
        SELECT
            t.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable,
            CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary,
            fk.foreign_table_name,
            fk.foreign_column_name
        FROM information_schema.tables t
        JOIN information_schema.columns c
            ON t.table_name = c.table_name
        LEFT JOIN (
            SELECT ku.table_name, ku.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage ku
                ON tc.constraint_name = ku.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
        ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
        LEFT JOIN (
            SELECT
                kcu.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
        ) fk ON c.table_name = fk.table_name AND c.column_name = fk.column_name
        WHERE t.table_schema = 'public'
        ORDER BY t.table_name, c.ordinal_position
        """

        try:
            # Try to acquire and use connection - if it fails, reconnect pool and retry
            assert self.pool is not None  # Type assertion for mypy
            async with self.pool.acquire() as conn:
                try:
                    # Try the actual query - if connection is dead, it will fail naturally
                    rows = await conn.fetch(meta_query)
                except (ConnectionDoesNotExistError, Exception) as e:
                    # If connection is dead, reconnect pool and let retry mechanism handle it
                    if (
                        isinstance(e, ConnectionDoesNotExistError)
                        or "connection" in str(e).lower()
                    ):
                        await self._reconnect_pool()
                        raise ConnectionDoesNotExistError(
                            f"Connection failed, pool reconnected: {e}"
                        ) from e
                    raise

                # Group by table
                tables = {}
                relationships = []

                for row in rows:
                    table_name = row["table_name"]

                    if table_name not in tables:
                        tables[table_name] = TableSchema(
                            name=table_name, columns=[], indexes=[]
                        )

                    column = ColumnSchema(
                        name=row["column_name"],
                        type=row["data_type"],
                        nullable=row["is_nullable"] == "YES",
                        primary_key=row["is_primary"],
                        foreign_key=(
                            f"{row['foreign_table_name']}.{row['foreign_column_name']}"
                            if row["foreign_table_name"]
                            else None
                        ),
                    )

                    tables[table_name].columns.append(column)

                    if row["foreign_table_name"]:
                        relationships.append(
                            {
                                "from": f"{table_name}.{row['column_name']}",
                                "to": f"{row['foreign_table_name']}.{row['foreign_column_name']}",
                            }
                        )

                # Get row counts for each table
                for table_name in list(tables.keys()):
                    try:
                        escaped_table_name = table_name.replace('"', '""')
                        count_query = f'SELECT COUNT(*) FROM "{escaped_table_name}"'
                        count = await conn.fetchval(count_query)
                        tables[table_name].row_count = count
                    except ConnectionDoesNotExistError:
                        raise
                    except Exception as e:
                        logging.getLogger(__name__).warning(
                            f"Failed to get row count for table {table_name}: {e}"
                        )
                        tables[table_name].row_count = 0

                self._schema = DatabaseSchema(
                    type="postgres",
                    name=self.connection_string.split("/")[-1].split("?")[0],
                    tables=tables,
                    relationships=relationships,
                )
                return self._schema

        except ConnectionDoesNotExistError:
            await self._reconnect_pool()
            raise

    async def execute(
        self, query: str, params: List[Any] | None = None, max_rows: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Executes a SQL query and returns the results.

        This method automatically adds a `LIMIT` clause to the query if one is not
        already present, to prevent excessive memory usage. It logs a warning if
        the number of returned rows reaches the specified limit.

        Args:
            query: The SQL query string to execute.
            params: A list of parameters to substitute into the query.
            max_rows: The maximum number of rows to return.

        Returns:
            A list of dictionaries, where each dictionary represents a result row.
        """
        logger = logging.getLogger(__name__)

        # Add LIMIT clause if not present to prevent memory issues
        query_upper = query.upper()
        if "LIMIT" not in query_upper:
            # Add LIMIT to the query
            query = f"{query.rstrip(';')} LIMIT {max_rows}"
            logger.debug(
                f"Added LIMIT {max_rows} to query without explicit limit")

        assert self.pool is not None  # Type assertion for mypy
        async with self.pool.acquire() as conn:
            if params:
                rows = await conn.fetch(query, *params)
            else:
                rows = await conn.fetch(query)

            # Warn if we hit the limit
            if len(rows) >= max_rows:
                logger.warning(
                    f"Query returned maximum rows ({max_rows}). Results may be truncated. "
                    f"Query: {query[:100]}..."
                )

            return [dict(row) for row in rows]

    async def health_check(self) -> bool:
        """
        Performs a health check on the database connection with retry logic.

        Handles transient errors common with PostgreSQL connection poolers.
        Retries up to 3 times with exponential backoff.

        Returns:
            `True` if the connection is healthy, `False` otherwise.
        """
        if not self.pool:
            return False

        # Check if pool is closing/closed and try to reconnect
        try:
            if self.pool.is_closing():
                logger = logging.getLogger(__name__)
                logger.warning(
                    "PostgreSQL pool is closing, attempting to reconnect...")
                try:
                    await self.connect()  # Reconnect
                except Exception as e:
                    logger.warning(f"Failed to reconnect PostgreSQL pool: {e}")
                    return False
        except AttributeError:
            # is_closing() may not be available in all asyncpg versions
            pass

        # Retry logic for transient errors (common with connection poolers)
        logger = logging.getLogger(__name__)
        for attempt in range(3):
            try:
                # Use timeout to prevent hanging on slow connections
                await asyncio.wait_for(self.pool.fetchval("SELECT 1"), timeout=5.0)
                return True
            except (asyncio.TimeoutError, Exception) as e:
                if attempt == 2:  # Last attempt
                    logger.warning(
                        f"PostgreSQL health check failed after {attempt + 1} attempts: {e}"
                    )
                    return False
                # Exponential backoff: 0.5s, 1s, 1.5s
                await asyncio.sleep(0.5 * (attempt + 1))

        return False
