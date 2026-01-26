"""Project store abstraction for managing projects within accounts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from app.core.account_keys import hash_api_key
from app.core.encryption import encrypt_database_url
from app.models.project import DatabaseConfig, Project


def _truncate_error_message(error: Exception, max_length: int = 200) -> str:
    """Truncate long error messages to keep logs clean."""
    error_str = str(error)
    # Remove verbose topology descriptions from MongoDB errors
    if "Topology Description" in error_str:
        # Extract just the main error message before topology details
        parts = error_str.split("Topology Description")
        if parts:
            error_str = parts[0].strip()

    # Truncate if still too long
    if len(error_str) > max_length:
        error_str = error_str[:max_length] + "..."

    return error_str


def generate_project_id() -> str:
    """
    Generate a secure, unique project ID using UUID.

    Returns:
        A UUID4-based project ID string (e.g., "prj_550e8400e29b41d4a716446655440000")
    """
    return f"prj_{uuid.uuid4().hex}"


class ProjectStore:
    """Abstract interface for project storage and retrieval."""

    async def get_by_api_key_async(self, api_key: str) -> Optional[Project]:
        """Lookup project by API key."""
        raise NotImplementedError

    async def get_by_id_async(self, project_id: str) -> Optional[Project]:
        """Lookup project by ID."""
        raise NotImplementedError

    async def list_by_account_async(self, account_id: str) -> List[Project]:
        """List all projects for an account."""
        raise NotImplementedError

    async def list_all_projects_async(self) -> List[Project]:
        """List all active projects across all accounts."""
        raise NotImplementedError

    async def create_project_async(
        self,
        name: str,
        account_id: str,
        api_key: str,
        postgres_url: str,
        mongodb_url: str,
        project_id: Optional[str] = None,
    ) -> Project:
        """Create a new project."""
        raise NotImplementedError

    async def update_project_async(
        self, project_id: str, **updates
    ) -> Optional[Project]:
        """Update project configuration."""
        raise NotImplementedError

    async def delete_project_async(self, project_id: str) -> bool:
        """Soft delete a project (set is_active=False)."""
        raise NotImplementedError

    async def rotate_api_key_async(
        self, project_id: str, new_api_key: str
    ) -> Optional[str]:
        """Rotate project API key. Returns old key hash for revocation tracking."""
        raise NotImplementedError


class MongoDBProjectStore(ProjectStore):
    """MongoDB-based project store for production use."""

    def __init__(self, mongo_url: str, db_name: str = "dbrevel_platform"):
        from motor.motor_asyncio import AsyncIOMotorClient

        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.mongo_url = mongo_url
        self.db_name = db_name

    async def _ensure_connected(self):
        """Ensure MongoDB connection is established."""
        if self.client is None:
            import logging

            logger = logging.getLogger(__name__)

            from motor.motor_asyncio import AsyncIOMotorClient

            self.client = AsyncIOMotorClient(
                self.mongo_url,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                maxPoolSize=10,
                minPoolSize=1,
                maxIdleTimeMS=45000,
                retryWrites=True,
                retryReads=True,
            )
            self.db = self.client[self.db_name]

            # Create indexes with error handling - don't fail if MongoDB has partial connectivity
            # Indexes will be created eventually when primary is available
            try:
                await self.db.projects.create_index("project_id", unique=True)
                await self.db.projects.create_index("account_id")
                await self.db.projects.create_index("api_key_hash")
                logger.debug("✓ Project store indexes created/verified")
            except Exception as e:
                # Log warning but don't fail - indexes may already exist or will be created later
                # This allows the app to continue even if MongoDB replica set has unreachable shards
                error_msg = _truncate_error_message(e)
                logger.warning(
                    f"Could not create project store indexes (may already exist or primary unavailable): {error_msg}. "
                    "The app will continue, but some operations may be slower until indexes are created."
                )

    async def get_by_api_key_async(self, api_key: str) -> Optional[Project]:
        """Lookup project by API key."""
        await self._ensure_connected()
        assert self.db is not None  # Type assertion for mypy

        import logging

        logger = logging.getLogger(__name__)
        logger.info(f"🔍 Looking up project by API key: {api_key[:20]}...")

        # Verify DB is connected
        if self.db is None:
            logger.error("❌ MongoDB database is None after _ensure_connected()")
            return None

        # Try direct lookup first (for backward compatibility)
        project_doc = await self.db.projects.find_one(
            {"api_key": api_key, "is_active": True}
        )
        if project_doc:
            logger.info(
                f"✓ Found project via direct lookup: {project_doc['name']} (ID: {project_doc['project_id']})"
            )
            return self._doc_to_project(project_doc)

        logger.info("  Direct lookup failed, trying hash-based lookup...")

        # Hash-based lookup
        api_key_hash = hash_api_key(api_key)
        project_doc = await self.db.projects.find_one(
            {"api_key_hash": api_key_hash, "is_active": True}
        )
        if project_doc:
            logger.info(
                f"✓ Found project via hash lookup: {project_doc['name']} (ID: {project_doc['project_id']})"
            )
            return self._doc_to_project(project_doc)

        logger.warning(f"⚠️  No project found for API key: {api_key[:20]}...")

        # Debug: Count total active projects to verify DB connection
        total_count = await self.db.projects.count_documents({"is_active": True})
        logger.info(f"  Total active projects in DB: {total_count}")

        return None

    async def get_by_id_async(self, project_id: str) -> Optional[Project]:
        """Lookup project by ID."""
        await self._ensure_connected()
        assert self.db is not None  # Type assertion for mypy
        project_doc = await self.db.projects.find_one({"project_id": project_id})
        if not project_doc:
            return None
        return self._doc_to_project(project_doc)

    async def list_by_account_async(self, account_id: str) -> List[Project]:
        """List all projects for an account."""
        await self._ensure_connected()
        assert self.db is not None  # Type assertion for mypy

        cursor = self.db.projects.find({"account_id": account_id})
        projects = []
        async for doc in cursor:
            projects.append(self._doc_to_project(doc))
        return projects

    async def list_all_projects_async(self) -> List[Project]:
        """List all active projects across all accounts."""
        await self._ensure_connected()
        assert self.db is not None  # Type assertion for mypy

        cursor = self.db.projects.find({"is_active": True})
        projects = []
        async for doc in cursor:
            projects.append(self._doc_to_project(doc))
        return projects

    async def create_project_async(
        self,
        name: str,
        account_id: str,
        api_key: str,
        postgres_url: str,
        mongodb_url: str,
        project_id: Optional[str] = None,
    ) -> Project:
        """Create a new project."""
        await self._ensure_connected()
        assert self.db is not None  # Type assertion for mypy

        if not project_id:
            project_id = generate_project_id()

        # Encrypt database URLs (idempotent — already-encrypted URLs are returned as-is
        # by encrypt_database_url since decrypt checks for scheme prefix)
        encrypted_pg_url = encrypt_database_url(postgres_url) if postgres_url else ""
        encrypted_mongo_url = encrypt_database_url(mongodb_url) if mongodb_url else ""

        # Build databases array from legacy URLs (for future use)
        databases_array = []
        if encrypted_pg_url:
            databases_array.append(
                {"type": "postgres", "connection_url": encrypted_pg_url}
            )
        if encrypted_mongo_url:
            databases_array.append(
                {"type": "mongodb", "connection_url": encrypted_mongo_url}
            )

        now = datetime.utcnow()
        project_doc = {
            "project_id": project_id,
            "name": name,
            "account_id": account_id,
            "api_key": api_key,
            "api_key_hash": hash_api_key(api_key),
            # Legacy fields (maintained for backward compatibility)
            "postgres_url": encrypted_pg_url,
            "mongodb_url": encrypted_mongo_url,
            # New format (for future use)
            "databases": databases_array,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
        }

        await self.db.projects.insert_one(project_doc)

        # Build databases list for Project model
        databases_list = []
        if encrypted_pg_url:
            databases_list.append(
                DatabaseConfig(type="postgres", connection_url=encrypted_pg_url)
            )
        if encrypted_mongo_url:
            databases_list.append(
                DatabaseConfig(type="mongodb", connection_url=encrypted_mongo_url)
            )

        return Project(
            id=project_id,
            name=name,
            account_id=account_id,
            api_key=api_key,
            postgres_url=encrypted_pg_url,
            mongodb_url=encrypted_mongo_url,
            databases=databases_list,
            created_at=now,
            updated_at=now,
            is_active=True,
        )

    async def update_project_async(
        self, project_id: str, **updates
    ) -> Optional[Project]:
        """Update project configuration."""
        await self._ensure_connected()
        assert self.db is not None  # Type assertion for mypy

        project_doc = await self.db.projects.find_one({"project_id": project_id})
        if not project_doc:
            return None

        # Encrypt database URLs if they're being updated
        if "postgres_url" in updates:
            if updates["postgres_url"]:
                updates["postgres_url"] = encrypt_database_url(updates["postgres_url"])
            else:
                updates["postgres_url"] = ""
        if "mongodb_url" in updates:
            if updates["mongodb_url"]:
                updates["mongodb_url"] = encrypt_database_url(updates["mongodb_url"])
            else:
                updates["mongodb_url"] = ""

        # Rebuild databases array when legacy URLs are updated (for future use)
        if "postgres_url" in updates or "mongodb_url" in updates:
            # Get current values (use updated values if provided, otherwise existing)
            final_pg_url = updates.get(
                "postgres_url", project_doc.get("postgres_url", "")
            )
            final_mongo_url = updates.get(
                "mongodb_url", project_doc.get("mongodb_url", "")
            )

            databases_array = []
            if final_pg_url and final_pg_url.strip():
                databases_array.append(
                    {"type": "postgres", "connection_url": final_pg_url}
                )
            if final_mongo_url and final_mongo_url.strip():
                databases_array.append(
                    {"type": "mongodb", "connection_url": final_mongo_url}
                )
            updates["databases"] = databases_array

        # Update timestamp
        updates["updated_at"] = datetime.utcnow()

        # Remove None values
        updates = {k: v for k, v in updates.items() if v is not None}

        assert self.db is not None  # Type assertion for mypy
        if updates:
            await self.db.projects.update_one(
                {"project_id": project_id}, {"$set": updates}
            )

        # Fetch updated project
        updated_doc = await self.db.projects.find_one({"project_id": project_id})
        return self._doc_to_project(updated_doc) if updated_doc else None

    async def delete_project_async(self, project_id: str) -> bool:
        """Soft delete a project (set is_active=False)."""
        await self._ensure_connected()
        assert self.db is not None  # Type assertion for mypy

        result = await self.db.projects.update_one(
            {"project_id": project_id},
            {"$set": {"is_active": False, "updated_at": datetime.utcnow()}},
        )
        return result.modified_count > 0

    async def rotate_api_key_async(
        self, project_id: str, new_api_key: str
    ) -> Optional[str]:
        """Rotate project API key. Returns old key hash for revocation tracking."""
        await self._ensure_connected()
        assert self.db is not None  # Type assertion for mypy

        project_doc = await self.db.projects.find_one({"project_id": project_id})
        if not project_doc:
            return None

        assert self.db is not None  # Type assertion for mypy
        old_key_hash = project_doc.get("api_key_hash")

        await self.db.projects.update_one(
            {"project_id": project_id},
            {
                "$set": {
                    "api_key": new_api_key,
                    "api_key_hash": hash_api_key(new_api_key),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        return old_key_hash

    def _migrate_legacy_databases(self, doc: dict) -> List[DatabaseConfig]:
        """
        Migrate legacy postgres_url/mongodb_url to new databases format.
        This ensures backward compatibility while supporting the new format.
        """
        databases = []

        # Check if new format exists
        if "databases" in doc and doc["databases"]:
            # New format already exists
            for db in doc["databases"]:
                databases.append(
                    DatabaseConfig(
                        type=db.get("type", ""),
                        connection_url=db.get("connection_url", ""),
                    )
                )
            return databases

        # Migrate from old format
        postgres_url = doc.get("postgres_url", "")
        mongodb_url = doc.get("mongodb_url", "")

        if postgres_url and postgres_url.strip() and not postgres_url.startswith("***"):
            databases.append(
                DatabaseConfig(type="postgres", connection_url=postgres_url)
            )

        if mongodb_url and mongodb_url.strip() and not mongodb_url.startswith("***"):
            databases.append(DatabaseConfig(type="mongodb", connection_url=mongodb_url))

        return databases

    def _doc_to_project(self, doc: dict) -> Project:
        """Convert MongoDB document to Project model with migration support."""
        databases = self._migrate_legacy_databases(doc)
        return Project(
            id=doc["project_id"],
            name=doc["name"],
            account_id=doc["account_id"],
            api_key=doc["api_key"],
            postgres_url=doc.get("postgres_url", ""),
            mongodb_url=doc.get("mongodb_url", ""),
            databases=databases,
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            is_active=doc.get("is_active", True),
        )


# Global project store instance (initialized in main.py)
project_store: Optional[ProjectStore] = None


def initialize_project_store(mongo_url: str, db_name: str = "dbrevel_platform"):
    """Initialize the global project store."""
    global project_store
    project_store = MongoDBProjectStore(mongo_url, db_name)
    return project_store


def get_project_store() -> Optional[ProjectStore]:
    """Get the global project store instance."""
    return project_store
