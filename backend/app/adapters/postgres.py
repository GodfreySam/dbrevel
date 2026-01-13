"""PostgreSQL database adapter"""
from typing import Any, Dict, List, Optional

import asyncpg
from app.adapters.base import DatabaseAdapter
from app.models.schema import ColumnSchema, DatabaseSchema, TableSchema


class PostgresAdapter(DatabaseAdapter):
    """PostgreSQL database adapter"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None
        self._schema: Optional[DatabaseSchema] = None

    async def connect(self) -> None:
        """Create connection pool"""
        # Disable statement cache for pgbouncer compatibility
        # pgbouncer with transaction/statement pool mode doesn't support prepared statements
        self.pool = await asyncpg.create_pool(
            self.connection_string,
            min_size=2,
            max_size=10,
            command_timeout=60,
            statement_cache_size=0  # Required for pgbouncer compatibility
        )

    async def disconnect(self) -> None:
        """Close connection pool"""
        if self.pool:
            await self.pool.close()

    async def introspect_schema(self) -> DatabaseSchema:
        """Introspect PostgreSQL schema"""

        if self._schema:
            return self._schema

        query = """
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

        rows = await self.pool.fetch(query)

        # Group by table
        tables = {}
        relationships = []

        for row in rows:
            table_name = row['table_name']

            if table_name not in tables:
                tables[table_name] = TableSchema(
                    name=table_name,
                    columns=[],
                    indexes=[]
                )

            column = ColumnSchema(
                name=row['column_name'],
                type=row['data_type'],
                nullable=row['is_nullable'] == 'YES',
                primary_key=row['is_primary'],
                foreign_key=f"{row['foreign_table_name']}.{row['foreign_column_name']}"
                if row['foreign_table_name'] else None
            )

            tables[table_name].columns.append(column)

            if row['foreign_table_name']:
                relationships.append({
                    'from': f"{table_name}.{row['column_name']}",
                    'to': f"{row['foreign_table_name']}.{row['foreign_column_name']}"
                })

        # Get row counts for each table
        for table_name in tables:
            try:
                # Validate table name against schema to prevent SQL injection
                if table_name not in tables:
                    tables[table_name].row_count = 0
                    continue

                # Use proper identifier quoting to prevent SQL injection
                # PostgreSQL double-quote escaping: replace " with ""
                escaped_table_name = table_name.replace('"', '""')
                query = f'SELECT COUNT(*) FROM "{escaped_table_name}"'
                count = await self.pool.fetchval(query)
                tables[table_name].row_count = count
            except Exception as e:
                # Log the error but continue with other tables
                import logging
                logging.getLogger(__name__).warning(
                    f"Failed to get row count for table {table_name}: {e}"
                )
                tables[table_name].row_count = 0

        self._schema = DatabaseSchema(
            type="postgres",
            name=self.connection_string.split('/')[-1],
            tables=tables,
            relationships=relationships
        )

        return self._schema

    async def execute(
        self,
        query: str,
        params: List[Any] = None,
        max_rows: int = 10000
    ) -> List[Dict[str, Any]]:
        """Execute SQL query with result size limits

        Args:
            query: SQL query string
            params: Query parameters
            max_rows: Maximum number of rows to return (default: 10000)

        Returns:
            List of result rows as dictionaries
        """
        import logging
        logger = logging.getLogger(__name__)

        # Add LIMIT clause if not present to prevent memory issues
        query_upper = query.upper()
        if "LIMIT" not in query_upper:
            # Add LIMIT to the query
            query = f"{query.rstrip(';')} LIMIT {max_rows}"
            logger.debug(f"Added LIMIT {max_rows} to query without explicit limit")

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
        """Check PostgreSQL health"""
        try:
            await self.pool.fetchval("SELECT 1")
            return True
        except Exception:
            return False
