"""MongoDB database adapter"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from app.adapters.base import DatabaseAdapter
from app.core.config import settings
from app.core.retry import with_retry
from app.models.schema import DatabaseSchema
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# MongoDB collection name validation pattern
# MongoDB collection names must not contain: \0, $, and must not start with system.
VALID_COLLECTION_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
logger = logging.getLogger(__name__)


class MongoDBAdapter(DatabaseAdapter):
    """MongoDB database adapter"""

    def __init__(self, connection_string: str, database: str):
        self.connection_string = connection_string
        self.database_name = database
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self._schema: Optional[DatabaseSchema] = None

    async def connect(self) -> None:
        """Connect to MongoDB with optimized connection pool settings"""
        # Configure connection pool for better reliability
        # These settings help with cloud database connections
        self.client = AsyncIOMotorClient(
            self.connection_string,
            serverSelectionTimeoutMS=10000,  # 10 second timeout for server selection
            connectTimeoutMS=10000,  # 10 second connection timeout
            socketTimeoutMS=30000,  # 30 second socket timeout
            maxPoolSize=settings.MONGODB_POOL_MAX_SIZE,  # Maximum connections in pool
            minPoolSize=settings.MONGODB_POOL_MIN_SIZE,  # Minimum connections in pool
            maxIdleTimeMS=45000,  # Close idle connections after 45s
            retryWrites=True,  # Retry writes on transient failures
            retryReads=True,  # Retry reads on transient failures
        )
        self.db = self.client[self.database_name]

        # Verify connection with a lightweight ping
        try:
            await self.client.admin.command("ping")
            logger.info(
                f"MongoDB connected to database '{self.database_name}' (pool: min={settings.MONGODB_POOL_MIN_SIZE}, max={settings.MONGODB_POOL_MAX_SIZE})"
            )
        except Exception as e:
            logger.warning(f"MongoDB ping failed: {e}. Connection may still work.")
            # Don't raise - let actual operations handle errors

    async def disconnect(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            try:
                # Close the client (this also stops background tasks)
                self.client.close()
                # Give it a moment to clean up background tasks
                await asyncio.sleep(0.1)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(f"Error closing MongoDB client: {e}")

    @with_retry(
        max_retries=3,
        initial_delay=1.0,
        max_delay=5.0,
        exceptions=(ConnectionFailure, ServerSelectionTimeoutError, Exception),
    )
    async def introspect_schema(self) -> DatabaseSchema:
        """Introspect MongoDB schema by sampling documents with retry logic"""

        if self._schema:
            return self._schema

        # Verify connection before introspection
        try:
            await self.client.admin.command("ping")
        except Exception as e:
            logger.warning(f"MongoDB connection check failed before introspection: {e}")
            # Try to reconnect
            await self.connect()

        collections = await self.db.list_collection_names()

        schema_data = {}

        for coll_name in collections:
            try:
                collection = self.db[coll_name]

                # Sample documents to infer schema (reduced sample size for faster introspection)
                sample_size = 50  # Reduced from 100 for faster startup
                documents = (
                    await collection.find()
                    .limit(sample_size)
                    .to_list(length=sample_size)
                )

                if not documents:
                    schema_data[coll_name] = {"fields": {}, "count": 0, "indexes": []}
                    continue

                # Infer fields from samples
                fields = {}
                for doc in documents:
                    for key, value in doc.items():
                        if key not in fields:
                            fields[key] = {
                                "type": type(value).__name__,
                                "nullable": False,
                                "examples": [],
                            }
                        if len(fields[key]["examples"]) < 3:
                            # Truncate long values
                            example_str = str(value)[:50]
                            if example_str not in fields[key]["examples"]:
                                fields[key]["examples"].append(example_str)

                # Get document count (with timeout)
                count = await collection.count_documents({})

                # Get indexes (with timeout)
                indexes = []
                try:
                    async for idx in collection.list_indexes():
                        indexes.append(str(idx.get("name", "")))
                except Exception as e:
                    logger.warning(
                        f"Failed to get indexes for collection {coll_name}: {e}"
                    )

                schema_data[coll_name] = {
                    "fields": fields,
                    "count": count,
                    "indexes": indexes,
                }
            except Exception as e:
                logger.warning(f"Failed to introspect collection {coll_name}: {e}")
                # Continue with other collections even if one fails
                schema_data[coll_name] = {"fields": {}, "count": 0, "indexes": []}

        self._schema = DatabaseSchema(
            type="mongodb", name=self.database_name, collections=schema_data
        )

        return self._schema

    async def execute(
        self,
        pipeline: List[Dict[str, Any]],
        collection: str = None,
        max_docs: int = 10000,
    ) -> List[Dict[str, Any]]:
        """Execute MongoDB aggregation pipeline with result size limits

        Args:
            pipeline: MongoDB aggregation pipeline
            collection: Collection name
            max_docs: Maximum number of documents to return (default: 10000)

        Returns:
            List of result documents

        Raises:
            ValueError: If collection name is invalid or missing
        """

        if collection:
            # Validate collection name to prevent NoSQL injection
            if not self._validate_collection_name(collection):
                raise ValueError(
                    f"Invalid collection name: {collection}. "
                    "Collection names must start with a letter or underscore and contain only alphanumeric characters and underscores."
                )
            coll = self.db[collection]
        else:
            # Try to extract collection from pipeline
            if pipeline and "collection" in pipeline[0]:
                collection = pipeline[0]["collection"]
                if not self._validate_collection_name(collection):
                    raise ValueError(
                        f"Invalid collection name in pipeline: {collection}"
                    )
                coll = self.db[collection]
                pipeline = pipeline[0].get("stages", pipeline)
            else:
                raise ValueError("Collection name required for MongoDB queries")

        # Add $limit stage if not present to prevent memory issues
        has_limit = any("$limit" in stage for stage in pipeline)
        if not has_limit:
            pipeline.append({"$limit": max_docs})
            logger.debug(f"Added $limit {max_docs} to pipeline without explicit limit")

        cursor = coll.aggregate(pipeline)
        results = await cursor.to_list(length=max_docs)

        # Warn if we hit the limit
        if len(results) >= max_docs:
            logger.warning(
                f"Query returned maximum documents ({max_docs}). Results may be truncated. "
                f"Collection: {collection}"
            )

        # Convert ObjectId to string for JSON serialization
        for doc in results:
            if "_id" in doc:
                doc["_id"] = str(doc["_id"])

        return results

    def _validate_collection_name(self, collection_name: str) -> bool:
        """Validate MongoDB collection name to prevent injection attacks

        Args:
            collection_name: Collection name to validate

        Returns:
            True if valid, False otherwise
        """
        if not collection_name or not isinstance(collection_name, str):
            return False

        # Check for dangerous patterns
        if collection_name.startswith("system."):
            return False

        if "\0" in collection_name or "$" in collection_name:
            return False

        # Check against whitelist pattern
        return bool(VALID_COLLECTION_NAME.match(collection_name))

    async def health_check(self) -> bool:
        """
        Check MongoDB health with retry logic.

        Handles transient connection errors and retries up to 3 times
        with exponential backoff.

        Returns:
            `True` if the connection is healthy, `False` otherwise.
        """
        if not self.client:
            return False

        # Retry logic for transient errors
        for attempt in range(3):
            try:
                # Use timeout to prevent hanging on slow connections
                await asyncio.wait_for(self.client.admin.command("ping"), timeout=5.0)
                return True
            except (
                asyncio.TimeoutError,
                ConnectionFailure,
                ServerSelectionTimeoutError,
                Exception,
            ) as e:
                if attempt == 2:  # Last attempt
                    logger.warning(
                        f"MongoDB health check failed after {attempt + 1} attempts: {e}"
                    )
                    return False
                # Exponential backoff: 0.5s, 1s, 1.5s
                await asyncio.sleep(0.5 * (attempt + 1))

        return False
