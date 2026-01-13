"""Project store abstraction for managing projects within accounts."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from app.core.encryption import decrypt_database_url, encrypt_database_url, mask_database_url
from app.core.account_keys import generate_account_key, hash_api_key, verify_api_key
from app.models.project import Project


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

    async def update_project_async(self, project_id: str, **updates) -> Optional[Project]:
        """Update project configuration."""
        raise NotImplementedError

    async def delete_project_async(self, project_id: str) -> bool:
        """Soft delete a project (set is_active=False)."""
        raise NotImplementedError

    async def rotate_api_key_async(self, project_id: str, new_api_key: str) -> Optional[str]:
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
            from motor.motor_asyncio import AsyncIOMotorClient

            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.db_name]
            # Create indexes
            await self.db.projects.create_index("project_id", unique=True)
            await self.db.projects.create_index("account_id")
            await self.db.projects.create_index("api_key_hash")

    async def get_by_api_key_async(self, api_key: str) -> Optional[Project]:
        """Lookup project by API key."""
        await self._ensure_connected()

        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 Looking up project by API key: {api_key[:20]}...")

        # Verify DB is connected
        if self.db is None:
            logger.error("❌ MongoDB database is None after _ensure_connected()")
            return None

        # Try direct lookup first (for backward compatibility)
        project_doc = await self.db.projects.find_one({"api_key": api_key, "is_active": True})
        if project_doc:
            logger.info(f"✓ Found project via direct lookup: {project_doc['name']} (ID: {project_doc['project_id']})")
            return self._doc_to_project(project_doc)

        logger.info(f"  Direct lookup failed, trying hash-based lookup...")

        # Hash-based lookup
        api_key_hash = hash_api_key(api_key)
        project_doc = await self.db.projects.find_one({"api_key_hash": api_key_hash, "is_active": True})
        if project_doc:
            logger.info(f"✓ Found project via hash lookup: {project_doc['name']} (ID: {project_doc['project_id']})")
            return self._doc_to_project(project_doc)

        logger.warning(f"⚠️  No project found for API key: {api_key[:20]}...")

        # Debug: Count total active projects to verify DB connection
        total_count = await self.db.projects.count_documents({"is_active": True})
        logger.info(f"  Total active projects in DB: {total_count}")

        return None

    async def get_by_id_async(self, project_id: str) -> Optional[Project]:
        """Lookup project by ID."""
        await self._ensure_connected()

        project_doc = await self.db.projects.find_one({"project_id": project_id})
        if not project_doc:
            return None

        return self._doc_to_project(project_doc)

    async def list_by_account_async(self, account_id: str) -> List[Project]:
        """List all projects for an account."""
        await self._ensure_connected()

        cursor = self.db.projects.find({"account_id": account_id})
        projects = []
        async for doc in cursor:
            projects.append(self._doc_to_project(doc))
        return projects

    async def list_all_projects_async(self) -> List[Project]:
        """List all active projects across all accounts."""
        await self._ensure_connected()

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

        if not project_id:
            project_id = generate_project_id()

        # Encrypt database URLs
        encrypted_pg_url = encrypt_database_url(postgres_url) if postgres_url else ""
        encrypted_mongo_url = encrypt_database_url(mongodb_url) if mongodb_url else ""

        now = datetime.utcnow()
        project_doc = {
            "project_id": project_id,
            "name": name,
            "account_id": account_id,
            "api_key": api_key,
            "api_key_hash": hash_api_key(api_key),
            "postgres_url": encrypted_pg_url,
            "mongodb_url": encrypted_mongo_url,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
        }

        await self.db.projects.insert_one(project_doc)

        return Project(
            id=project_id,
            name=name,
            account_id=account_id,
            api_key=api_key,
            postgres_url=encrypted_pg_url,
            mongodb_url=encrypted_mongo_url,
            created_at=now,
            updated_at=now,
            is_active=True,
        )

    async def update_project_async(self, project_id: str, **updates) -> Optional[Project]:
        """Update project configuration."""
        await self._ensure_connected()

        project_doc = await self.db.projects.find_one({"project_id": project_id})
        if not project_doc:
            return None

        # Encrypt database URLs if they're being updated
        if "postgres_url" in updates and updates["postgres_url"]:
            updates["postgres_url"] = encrypt_database_url(updates["postgres_url"])
        if "mongodb_url" in updates and updates["mongodb_url"]:
            updates["mongodb_url"] = encrypt_database_url(updates["mongodb_url"])

        # Update timestamp
        updates["updated_at"] = datetime.utcnow()

        # Remove None values
        updates = {k: v for k, v in updates.items() if v is not None}

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

        result = await self.db.projects.update_one(
            {"project_id": project_id}, {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def rotate_api_key_async(self, project_id: str, new_api_key: str) -> Optional[str]:
        """Rotate project API key. Returns old key hash for revocation tracking."""
        await self._ensure_connected()

        project_doc = await self.db.projects.find_one({"project_id": project_id})
        if not project_doc:
            return None

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

    def _doc_to_project(self, doc: dict) -> Project:
        """Convert MongoDB document to Project model."""
        return Project(
            id=doc["project_id"],
            name=doc["name"],
            account_id=doc["account_id"],
            api_key=doc["api_key"],
            postgres_url=doc.get("postgres_url", ""),
            mongodb_url=doc.get("mongodb_url", ""),
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
