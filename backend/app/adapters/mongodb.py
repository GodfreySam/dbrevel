"""MongoDB database adapter"""
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Any, Dict, List, Optional
import re
import logging
from app.adapters.base import DatabaseAdapter
from app.models.schema import DatabaseSchema

# MongoDB collection name validation pattern
# MongoDB collection names must not contain: \0, $, and must not start with system.
VALID_COLLECTION_NAME = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
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
        """Connect to MongoDB"""
        self.client = AsyncIOMotorClient(self.connection_string)
        self.db = self.client[self.database_name]
        
    async def disconnect(self) -> None:
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            
    async def introspect_schema(self) -> DatabaseSchema:
        """Introspect MongoDB schema by sampling documents"""
        
        if self._schema:
            return self._schema
            
        collections = await self.db.list_collection_names()
        
        schema_data = {}
        
        for coll_name in collections:
            collection = self.db[coll_name]
            
            # Sample documents to infer schema
            sample_size = 100
            documents = await collection.find().limit(sample_size).to_list(length=sample_size)
            
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
                            "examples": []
                        }
                    if len(fields[key]["examples"]) < 3:
                        # Truncate long values
                        example_str = str(value)[:50]
                        if example_str not in fields[key]["examples"]:
                            fields[key]["examples"].append(example_str)
                        
            # Get document count
            count = await collection.count_documents({})
            
            # Get indexes
            indexes = []
            async for idx in collection.list_indexes():
                indexes.append(str(idx.get('name', '')))
            
            schema_data[coll_name] = {
                "fields": fields,
                "count": count,
                "indexes": indexes
            }
            
        self._schema = DatabaseSchema(
            type="mongodb",
            name=self.database_name,
            collections=schema_data
        )
        
        return self._schema
        
    async def execute(
        self,
        pipeline: List[Dict[str, Any]],
        collection: str = None,
        max_docs: int = 10000
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
            if pipeline and 'collection' in pipeline[0]:
                collection = pipeline[0]['collection']
                if not self._validate_collection_name(collection):
                    raise ValueError(f"Invalid collection name in pipeline: {collection}")
                coll = self.db[collection]
                pipeline = pipeline[0].get('stages', pipeline)
            else:
                raise ValueError("Collection name required for MongoDB queries")

        # Add $limit stage if not present to prevent memory issues
        has_limit = any('$limit' in stage for stage in pipeline)
        if not has_limit:
            pipeline.append({'$limit': max_docs})
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
            if '_id' in doc:
                doc['_id'] = str(doc['_id'])

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
        if collection_name.startswith('system.'):
            return False

        if '\0' in collection_name or '$' in collection_name:
            return False

        # Check against whitelist pattern
        return bool(VALID_COLLECTION_NAME.match(collection_name))
        
    async def health_check(self) -> bool:
        """Check MongoDB health"""
        try:
            await self.client.admin.command('ping')
            return True
        except Exception:
            return False
