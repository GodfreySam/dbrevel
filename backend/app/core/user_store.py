"""User store for managing user accounts in MongoDB."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.core.auth import hash_password, verify_password
from app.models.user import User
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient


def _truncate_error_message(error: Exception, max_length: int = 200) -> str:
    """Truncate long error messages to keep logs clean."""
    error_str = str(error)
    # Remove verbose topology descriptions from MongoDB errors
    if "Topology Description" in error_str:
        parts = error_str.split("Topology Description")
        if parts:
            error_str = parts[0].strip()
    
    # Truncate if still too long
    if len(error_str) > max_length:
        error_str = error_str[:max_length] + "..."
    
    return error_str


class UserStore:
    """Store for managing user accounts."""

    def __init__(self, mongo_url: str, db_name: str = "dbrevel_platform"):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.mongo_url = mongo_url
        self.db_name = db_name

    async def _ensure_connected(self):
        """Ensure MongoDB connection is established."""
        import logging
        logger = logging.getLogger(__name__)
        
        if self.client is None:
            logger.info("[UserStore] Creating new MongoDB client connection...")
            from motor.motor_asyncio import AsyncIOMotorClient
            self.client = AsyncIOMotorClient(self.mongo_url)
            self.db = self.client[self.db_name]
            logger.info("[UserStore] MongoDB client created, creating indexes...")
            # Create indexes with error handling - don't fail if MongoDB has partial connectivity
            try:
                await self.db.users.create_index("email", unique=True)
                await self.db.users.create_index("account_id")
                logger.info("[UserStore] MongoDB indexes created")
            except Exception as e:
                # Log warning but don't fail - indexes may already exist or will be created later
                error_msg = _truncate_error_message(e)
                logger.warning(
                    f"Could not create user store indexes (may already exist or primary unavailable): {error_msg}. "
                    "The app will continue, but some operations may be slower until indexes are created."
                )
        else:
            logger.debug("[UserStore] MongoDB client already exists")

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID (MongoDB _id)."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[UserStore] get_by_id called with user_id={user_id}")
        
        logger.info("[UserStore] Ensuring MongoDB connection...")
        await self._ensure_connected()
        logger.info("[UserStore] MongoDB connection ensured")
        
        try:
            logger.info(f"[UserStore] Querying MongoDB for user _id={user_id}")
            doc = await self.db.users.find_one({"_id": ObjectId(user_id)})
            logger.info(f"[UserStore] MongoDB query completed: found={doc is not None}")
            if doc:
                user = self._doc_to_user(doc)
                logger.info(f"[UserStore] User converted: {user.email if user else 'None'}")
                return user
        except Exception as e:
            logger.error(f"[UserStore] Exception in get_by_id: {e}", exc_info=True)
            # Invalid ObjectId format
            return None
        logger.info(f"[UserStore] User not found for user_id={user_id}")
        return None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        await self._ensure_connected()
        doc = await self.db.users.find_one({"email": email})
        if doc:
            return self._doc_to_user(doc)
        return None

    async def create_user(
        self, email: str, password: str, account_id: str
    ) -> User:
        """Create a new user."""
        await self._ensure_connected()

        # Check if user already exists
        existing = await self.get_by_email(email)
        if existing:
            raise ValueError(f"User with email {email} already exists")

        # Create user document (MongoDB will auto-generate _id)
        password_hash = hash_password(password)
        created_at = datetime.utcnow()

        user_doc = {
            "email": email,
            "password_hash": password_hash,
            "account_id": account_id,
            "created_at": created_at,
            "last_login": None,
            "email_verified": False,  # New users start unverified
        }

        # Insert and get the auto-generated _id
        result = await self.db.users.insert_one(user_doc)
        user_id = str(result.inserted_id)

        # Create User object with MongoDB _id as string
        user = User(
            id=user_id,
            email=email,
            password_hash=password_hash,
            account_id=account_id,
            created_at=created_at,
        )

        return user

    async def verify_user(self, email: str, password: str) -> Optional[User]:
        """Verify user credentials."""
        user = await self.get_by_email(email)
        if not user:
            return None

        if not verify_password(password, user.password_hash):
            return None

        # Update last login
        await self.db.users.update_one(
            {"_id": ObjectId(user.id)},
            {"$set": {"last_login": datetime.utcnow()}},
        )
        user.last_login = datetime.utcnow()

        return user

    def _doc_to_user(self, doc: dict) -> User:
        """Convert MongoDB document to User."""
        # Use _id (MongoDB's auto-generated ID)
        user_id = str(doc["_id"])

        # Require `account_id` field (legacy `tenant_id` removed)
        account_id = doc.get("account_id")
        if not account_id:
            raise ValueError(
                f"User document missing required 'account_id' field: {doc.get('email')}")

        return User(
            id=user_id,
            email=doc["email"],
            password_hash=doc["password_hash"],
            account_id=account_id,
            created_at=doc["created_at"],
            last_login=doc.get("last_login"),
            # Default to False for existing users
            email_verified=doc.get("email_verified", False),
            # Get role from database, default to "user"
            role=doc.get("role", "user"),
        )

    async def mark_email_verified(self, user_id: str) -> bool:
        """Mark a user's email as verified."""
        import logging
        await self._ensure_connected()

        # Log before update
        user_before = await self.get_by_id(user_id)
        if user_before:
            logging.info(
                f"mark_email_verified: Updating user {user_id} (email={user_before.email}) "
                f"from email_verified={user_before.email_verified} to True"
            )

        result = await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"email_verified": True}}
        )

        # Verify the update was successful
        if result.modified_count > 0:
            user_after = await self.get_by_id(user_id)
            if user_after:
                logging.info(
                    f"mark_email_verified: Successfully updated user {user_id}. "
                    f"email_verified is now {user_after.email_verified}"
                )
            else:
                logging.error(
                    f"mark_email_verified: User {user_id} not found after update!")
            return True
        else:
            logging.warning(
                f"mark_email_verified: Update returned modified_count={result.modified_count} for user {user_id}. "
                f"User may not exist or email already verified."
            )
            return False

    async def update_user(
        self,
        user_id: str,
        role: Optional[str] = None,
        email_verified: Optional[bool] = None,
    ) -> Optional[User]:
        """Update user fields (role, email_verified)."""
        await self._ensure_connected()

        # Build update dict with only provided fields
        update_fields = {}
        if role is not None:
            if role not in ("user", "admin"):
                raise ValueError("Role must be 'user' or 'admin'")
            update_fields["role"] = role
        if email_verified is not None:
            update_fields["email_verified"] = email_verified

        if not update_fields:
            # Nothing to update, return current user
            return await self.get_by_id(user_id)

        result = await self.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            return None

        return await self.get_by_id(user_id)

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user by ID."""
        await self._ensure_connected()

        result = await self.db.users.delete_one({"_id": ObjectId(user_id)})
        return result.deleted_count > 0


# Global user store instance
# Will be initialized with MongoDB connection
user_store: Optional[UserStore] = None


def init_user_store(mongo_url: str, db_name: str = "dbrevel_platform"):
    """Initialize the global user store."""
    global user_store
    user_store = UserStore(mongo_url, db_name)
    return user_store


def get_user_store() -> Optional[UserStore]:
    """Get the global user store instance."""
    return user_store
