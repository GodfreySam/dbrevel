"""Account store abstraction for managing accounts.

This module provides a simple abstract `AccountStore` interface along with
in-memory, file-backed and MongoDB-backed implementations used by the
application. A small set of helper utilities used by the store are
implemented here as well (e.g. `generate_account_id`).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from app.core.account_keys import hash_api_key, verify_api_key
from app.core.accounts import AccountConfig
from app.core.encryption import encrypt_database_url


def generate_account_id() -> str:
    """Generate a short unique account id (UUID4 hex)."""
    return uuid4().hex


class AccountStore:
    """Abstract-ish base for account stores.

    Methods raise `NotImplementedError` and are implemented by concrete
    subclasses in this module.
    """

    async def get_by_api_key_async(self, api_key: str) -> Optional[AccountConfig]:
        """Lookup account by API key."""
        raise NotImplementedError

    async def get_by_id_async(self, account_id: str) -> Optional[AccountConfig]:
        """Lookup account by ID."""
        raise NotImplementedError

    async def list_accounts_async(self) -> List[AccountConfig]:
        """List all accounts."""
        raise NotImplementedError

    async def create_account_async(
        self,
        name: str,
        api_key: str,
        postgres_url: str,
        mongodb_url: str,
        gemini_mode: str = "platform",
        gemini_api_key: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> AccountConfig:
        """Create a new account."""
        raise NotImplementedError

    async def update_account_async(self, account_id: str, **updates) -> Optional[AccountConfig]:
        """Update account configuration."""
        raise NotImplementedError

    async def delete_account_async(self, account_id: str) -> bool:
        """Delete an account."""
        raise NotImplementedError

    async def rotate_api_key_async(self, account_id: str, new_api_key: str) -> Optional[str]:
        """Rotate account API key. Returns old key hash for revocation tracking."""
        raise NotImplementedError


class InMemoryAccountStore(AccountStore):
    """In-memory account store (for development/testing)."""

    def __init__(self):
        self._accounts_by_id: Dict[str, AccountConfig] = {}
        self._accounts_by_key: Dict[str, AccountConfig] = {}
        self._key_hashes: Dict[str, str] = {}  # account_id -> key_hash

    async def get_by_api_key_async(self, api_key: str) -> Optional[AccountConfig]:
        """Lookup account by API key (supports both raw keys and hashed lookups)."""
        # Direct lookup (for backward compatibility)
        if api_key in self._accounts_by_key:
            return self._accounts_by_key[api_key]

        # Hash-based lookup (more secure)
        for account_id, stored_hash in self._key_hashes.items():
            if verify_api_key(api_key, stored_hash):
                account = self._accounts_by_id.get(account_id)
                if account:
                    # Update direct lookup for performance
                    self._accounts_by_key[api_key] = account
                    return account

        return None

    async def get_by_id_async(self, account_id: str) -> Optional[AccountConfig]:
        return self._accounts_by_id.get(account_id)

    async def list_accounts_async(self) -> List[AccountConfig]:
        return list(self._accounts_by_id.values())

    async def create_account_async(
        self,
        name: str,
        api_key: str,
        postgres_url: str,
        mongodb_url: str,
        gemini_mode: str = "platform",
        gemini_api_key: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> AccountConfig:
        # Use provided account_id, or generate one
        if account_id:
            if account_id in self._accounts_by_id:
                raise ValueError(
                    f"Account with ID '{account_id}' already exists")
        else:
            # Generate secure UUID-based account ID
            account_id = generate_account_id()
            # Ensure uniqueness (unlikely collision, but be safe)
            while account_id in self._accounts_by_id:
                account_id = generate_account_id()

        # Encrypt database URLs before storing
        encrypted_pg_url = encrypt_database_url(
            postgres_url) if postgres_url else ""
        encrypted_mongo_url = encrypt_database_url(
            mongodb_url) if mongodb_url else ""

        account = AccountConfig(
            id=account_id,
            name=name,
            api_key=api_key,
            postgres_url=encrypted_pg_url,  # Store encrypted
            mongodb_url=encrypted_mongo_url,  # Store encrypted
            gemini_mode=gemini_mode,
            gemini_api_key=gemini_api_key,
        )

        self._accounts_by_id[account_id] = account
        self._accounts_by_key[api_key] = account
        self._key_hashes[account_id] = hash_api_key(api_key)

        return account

    async def update_account_async(self, account_id: str, **updates) -> Optional[AccountConfig]:
        account = self._accounts_by_id.get(account_id)
        if not account:
            return None

        # Encrypt database URLs if they're being updated
        if "postgres_url" in updates and updates["postgres_url"]:
            updates["postgres_url"] = encrypt_database_url(
                updates["postgres_url"])
        if "mongodb_url" in updates and updates["mongodb_url"]:
            updates["mongodb_url"] = encrypt_database_url(
                updates["mongodb_url"])

        # Update fields
        for key, value in updates.items():
            if hasattr(account, key) and value is not None:
                setattr(account, key, value)

        # If API key changed, update lookups
        if "api_key" in updates:
            old_key = account.api_key
            new_key = updates["api_key"]
            if old_key in self._accounts_by_key:
                del self._accounts_by_key[old_key]
            self._accounts_by_key[new_key] = account
            self._key_hashes[account_id] = hash_api_key(new_key)

        return account

    async def delete_account_async(self, account_id: str) -> bool:
        account = self._accounts_by_id.get(account_id)
        if not account:
            return False

        # Remove from all lookups
        if account.api_key in self._accounts_by_key:
            del self._accounts_by_key[account.api_key]
        if account_id in self._key_hashes:
            del self._key_hashes[account_id]
        del self._accounts_by_id[account_id]

        return True

    async def rotate_api_key_async(self, account_id: str, new_api_key: str) -> Optional[str]:
        account = self._accounts_by_id.get(account_id)
        if not account:
            return None

        old_key_hash = self._key_hashes.get(account_id)
        old_key = account.api_key

        # Update account
        account.api_key = new_api_key

        # Update lookups
        if old_key in self._accounts_by_key:
            del self._accounts_by_key[old_key]
        self._accounts_by_key[new_api_key] = account
        self._key_hashes[account_id] = hash_api_key(new_api_key)

        return old_key_hash


class FileAccountStore(AccountStore):
    """File-based account store (JSON file for persistence)."""

    def __init__(self, file_path: str = "accounts.json"):
        self.file_path = Path(file_path)
        self._accounts_by_id: Dict[str, AccountConfig] = {}
        self._accounts_by_key: Dict[str, AccountConfig] = {}
        self._key_hashes: Dict[str, str] = {}
        self._load_from_file()

    def _load_from_file(self):
        """Load accounts from JSON file."""
        if not self.file_path.exists():
            return

        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
                for account_data in data.get("accounts", []):
                    account = AccountConfig(**account_data)
                    self._accounts_by_id[account.id] = account
                    self._accounts_by_key[account.api_key] = account
                    # Note: In file-based store, we store keys in plain text
                    # In production, you'd want to encrypt or hash these
                    self._key_hashes[account.id] = hash_api_key(
                        account.api_key)
        except Exception as e:
            print(f"Error loading accounts from file: {e}")

    def _save_to_file(self):
        """Save accounts to JSON file."""
        data = {
            "accounts": [
                {
                    "id": account.id,
                    "name": account.name,
                    "api_key": account.api_key,  # In production, store hashed
                    "postgres_url": account.postgres_url,
                    "mongodb_url": account.mongodb_url,
                    "gemini_mode": account.gemini_mode,
                    "gemini_api_key": account.gemini_api_key,
                }
                for account in self._accounts_by_id.values()
            ]
        }

        try:
            with open(self.file_path, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving accounts to file: {e}")

    async def get_by_api_key_async(self, api_key: str) -> Optional[AccountConfig]:
        if api_key in self._accounts_by_key:
            return self._accounts_by_key[api_key]

        for account_id, stored_hash in self._key_hashes.items():
            if verify_api_key(api_key, stored_hash):
                account = self._accounts_by_id.get(account_id)
                if account:
                    self._accounts_by_key[api_key] = account
                    return account

        return None

    async def get_by_id_async(self, account_id: str) -> Optional[AccountConfig]:
        return self._accounts_by_id.get(account_id)

    async def list_accounts_async(self) -> List[AccountConfig]:
        return list(self._accounts_by_id.values())

    async def create_account_async(
        self,
        name: str,
        api_key: str,
        postgres_url: str,
        mongodb_url: str,
        gemini_mode: str = "platform",
        gemini_api_key: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> AccountConfig:
        # Use provided account_id, or generate one
        if account_id:
            if account_id in self._accounts_by_id:
                raise ValueError(
                    f"Account with ID '{account_id}' already exists")
        else:
            # Generate secure UUID-based account ID
            account_id = generate_account_id()
            # Ensure uniqueness (unlikely collision, but be safe)
            while account_id in self._accounts_by_id:
                account_id = generate_account_id()

        # Encrypt database URLs before storing
        encrypted_pg_url = encrypt_database_url(
            postgres_url) if postgres_url else ""
        encrypted_mongo_url = encrypt_database_url(
            mongodb_url) if mongodb_url else ""

        account = AccountConfig(
            id=account_id,
            name=name,
            api_key=api_key,
            postgres_url=encrypted_pg_url,  # Store encrypted
            mongodb_url=encrypted_mongo_url,  # Store encrypted
            gemini_mode=gemini_mode,
            gemini_api_key=gemini_api_key,
        )

        self._accounts_by_id[account_id] = account
        self._accounts_by_key[api_key] = account
        self._key_hashes[account_id] = hash_api_key(api_key)

        self._save_to_file()
        return account

    async def update_account_async(self, account_id: str, **updates) -> Optional[AccountConfig]:
        account = self._accounts_by_id.get(account_id)
        if not account:
            return None

        # Encrypt database URLs if they're being updated
        if "postgres_url" in updates and updates["postgres_url"]:
            updates["postgres_url"] = encrypt_database_url(
                updates["postgres_url"])
        if "mongodb_url" in updates and updates["mongodb_url"]:
            updates["mongodb_url"] = encrypt_database_url(
                updates["mongodb_url"])

        for key, value in updates.items():
            if hasattr(account, key) and value is not None:
                setattr(account, key, value)

        if "api_key" in updates:
            old_key = account.api_key
            new_key = updates["api_key"]
            if old_key in self._accounts_by_key:
                del self._accounts_by_key[old_key]
            self._accounts_by_key[new_key] = account
            self._key_hashes[account_id] = hash_api_key(new_key)

        self._save_to_file()
        return account

    async def delete_account_async(self, account_id: str) -> bool:
        account = self._accounts_by_id.get(account_id)
        if not account:
            return False

        if account.api_key in self._accounts_by_key:
            del self._accounts_by_key[account.api_key]
        if account_id in self._key_hashes:
            del self._key_hashes[account_id]
        del self._accounts_by_id[account_id]

        self._save_to_file()
        return True

    async def rotate_api_key_async(self, account_id: str, new_api_key: str) -> Optional[str]:
        account = self._accounts_by_id.get(account_id)
        if not account:
            return None

        old_key_hash = self._key_hashes.get(account_id)
        old_key = account.api_key

        account.api_key = new_api_key

        if old_key in self._accounts_by_key:
            del self._accounts_by_key[old_key]
        self._accounts_by_key[new_api_key] = account
        self._key_hashes[account_id] = hash_api_key(new_api_key)

        self._save_to_file()
        return old_key_hash


class MongoDBAccountStore(AccountStore):
    """MongoDB-based account store for production use."""

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

            from motor.motor_asyncio import AsyncIOMotorClient
            logging.info(
                f"MongoDBAccountStore: Connecting to MongoDB URL: {self.mongo_url}, database: {self.db_name}")
            # Configure connection pool for better reliability and to reduce background reconnection noise
            self.client = AsyncIOMotorClient(
                self.mongo_url,
                serverSelectionTimeoutMS=10000,  # 10 second timeout for server selection
                connectTimeoutMS=10000,  # 10 second connection timeout
                socketTimeoutMS=30000,  # 30 second socket timeout
                maxPoolSize=10,  # Maximum connections in pool
                minPoolSize=1,  # Minimum connections in pool
                maxIdleTimeMS=45000,  # Close idle connections after 45s
                retryWrites=True,  # Retry writes on transient failures
                retryReads=True,  # Retry reads on transient failures
            )
            self.db = self.client[self.db_name]
            # Verify connection by pinging
            await self.client.admin.command('ping')
            logging.info(
                f"MongoDBAccountStore: Connected to database '{self.db_name}'")
            # Create indexes
            await self.db.users.create_index("email", unique=True)
            await self.db.users.create_index("account_id")
            await self.db.accounts.create_index("account_id", unique=True)
            await self.db.accounts.create_index("api_key_hash")
            logging.info(f"MongoDBAccountStore: Indexes created/verified")

    async def get_by_api_key_async(self, api_key: str) -> Optional[AccountConfig]:
        """Async version of get_by_api_key."""
        await self._ensure_connected()

        # Try direct lookup first (for backward compatibility)
        account_doc = await self.db.accounts.find_one({"api_key": api_key})
        if account_doc:
            return self._doc_to_account(account_doc)

        # Hash-based lookup
        api_key_hash = hash_api_key(api_key)
        account_doc = await self.db.accounts.find_one({"api_key_hash": api_key_hash})
        if account_doc:
            return self._doc_to_account(account_doc)

        return None

    async def get_by_id_async(self, account_id: str) -> Optional[AccountConfig]:
        """Async version of get_by_id."""
        await self._ensure_connected()

        # Log for debugging
        import logging
        logging.debug(
            f"MongoDBAccountStore: Querying for account_id={account_id}")

        account_doc = await self.db.accounts.find_one({"account_id": account_id})
        if account_doc:
            logging.debug(
                f"MongoDBAccountStore: Found account document for account_id={account_id}")
            return self._doc_to_account(account_doc)
        else:
            # Try legacy fallbacks: some older records used tenant_id or legacy_tenant_id
            try:
                legacy_doc = await self.db.accounts.find_one({"$or": [{"tenant_id": account_id}, {"legacy_tenant_id": account_id}]})
                if legacy_doc:
                    logging.warning(
                        f"MongoDBAccountStore: Found account via legacy field for account_id={account_id}")
                    return self._doc_to_account(legacy_doc)
            except Exception:
                # ignore errors in legacy lookup
                pass

            # Try mapping via projects collection: find a project that references this legacy tenant id
            try:
                proj = await self.db.projects.find_one({"$or": [{"tenant_id": account_id}, {"account_id": account_id}]}, {"account_id": 1})
                if proj and proj.get("account_id"):
                    mapped_id = proj.get("account_id")
                    mapped_doc = await self.db.accounts.find_one({"account_id": mapped_id})
                    if mapped_doc:
                        logging.warning(
                            f"MongoDBAccountStore: Mapped legacy account_id {account_id} -> {mapped_id} via projects collection")
                        return self._doc_to_account(mapped_doc)
            except Exception:
                pass

            # Log all account_ids in database for debugging
            all_docs = await self.db.accounts.find({}, {"account_id": 1}).to_list(length=100)
            all_ids = [doc.get("account_id") for doc in all_docs]
            logging.warning(
                f"MongoDBAccountStore: Account not found for account_id={account_id}. "
                f"Available account_ids in database: {all_ids}"
            )
        return None

    async def list_accounts_async(self) -> List[AccountConfig]:
        """Async version of list_accounts."""
        await self._ensure_connected()
        cursor = self.db.accounts.find({})
        accounts = []
        async for doc in cursor:
            accounts.append(self._doc_to_account(doc))
        return accounts

    async def create_account_async(
        self,
        name: str,
        api_key: str,
        postgres_url: str,
        mongodb_url: str,
        gemini_mode: str = "platform",
        gemini_api_key: Optional[str] = None,
        account_id: Optional[str] = None,
    ) -> AccountConfig:
        """Async version of create_account."""
        await self._ensure_connected()

        import logging

        # Use provided account_id, or generate one
        if account_id:
            # Check if account_id already exists
            existing = await self.db.accounts.find_one({"account_id": account_id})
            if existing:
                raise ValueError(
                    f"Account with ID '{account_id}' already exists")
        else:
            # Generate secure UUID-based account ID
            account_id = generate_account_id()
            # Ensure uniqueness (unlikely collision with UUID, but be safe)
            while await self.db.accounts.find_one({"account_id": account_id}):
                account_id = generate_account_id()

        account = AccountConfig(
            id=account_id,
            name=name,
            api_key=api_key,
            postgres_url=postgres_url,
            mongodb_url=mongodb_url,
            gemini_mode=gemini_mode,
            gemini_api_key=gemini_api_key,
        )

        # Store in MongoDB
        account_doc = {
            "account_id": account_id,
            "name": name,
            "api_key": api_key,  # Store plain for backward compatibility
            "api_key_hash": hash_api_key(api_key),
            "postgres_url": postgres_url,
            "mongodb_url": mongodb_url,
            "gemini_mode": gemini_mode,
            "gemini_api_key": gemini_api_key,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        # Validate database name
        if not self.db_name or self.db_name.strip() == "":
            logging.error(
                f"MongoDBAccountStore: CRITICAL - Database name is empty or invalid!")
            raise RuntimeError("Database name is empty or invalid")

        # Log database info before insert
        logging.info(
            f"MongoDBAccountStore: Inserting account {account_id} into database '{self.db_name}', "
            f"collection 'accounts', MongoDB URL: {self.mongo_url}"
        )

        # Insert with explicit write concern to ensure persistence
        # w=1 means write must be acknowledged by at least one node
        # j=True means write must be written to journal (for durability)
        result = await self.db.accounts.insert_one(
            account_doc,
            # Note: Motor doesn't support write concern in insert_one directly
            # We'll verify acknowledgment and then query to confirm
        )

        logging.info(
            f"MongoDBAccountStore: Created account with account_id={account_id}, "
            f"MongoDB _id={result.inserted_id}, acknowledged={result.acknowledged}"
        )

        # Ensure write is acknowledged
        if not result.acknowledged:
            logging.error(
                f"MongoDBAccountStore: CRITICAL - Account {account_id} insert was not acknowledged by MongoDB! "
                f"Database: {self.db_name}, Collection: accounts"
            )
            raise RuntimeError(
                f"Account {account_id} insert was not acknowledged by MongoDB. "
                f"Database: {self.db_name}"
            )

        # Force a write to journal by performing a read operation (ensures write is flushed)
        # This helps with MongoDB write propagation delays
        try:
            await self.db.accounts.find_one({"_id": result.inserted_id}, {"_id": 1})
            logging.debug(
                f"MongoDBAccountStore: Confirmed account document exists with _id={result.inserted_id}")
        except Exception as e:
            logging.warning(
                f"MongoDBAccountStore: Could not immediately read back account document: {e}")

        # Verify the account was inserted by querying it back with retry
        import asyncio
        verify_doc = None
        for verify_attempt in range(3):
            verify_doc = await self.db.accounts.find_one({"account_id": account_id})
            if verify_doc:
                logging.info(
                    f"MongoDBAccountStore: Verified account {account_id} exists in database (attempt {verify_attempt + 1})"
                )
                break
            if verify_attempt < 2:
                logging.warning(
                    f"MongoDBAccountStore: Account {account_id} not found on attempt {verify_attempt + 1}, retrying..."
                )
                await asyncio.sleep(0.2)

        if not verify_doc:
            # Log all accounts for debugging
            all_docs = await self.db.accounts.find({}, {"account_id": 1}).to_list(length=100)
            all_ids = [doc.get("account_id") for doc in all_docs]
            logging.error(
                f"MongoDBAccountStore: CRITICAL - Account {account_id} was inserted but cannot be retrieved! "
                f"Database: {self.db_name}, Collection: accounts, Available account_ids: {all_ids}"
            )
            raise RuntimeError(
                f"Account {account_id} was inserted but cannot be retrieved immediately. "
                f"Database: {self.db_name}, Available account_ids: {all_ids}"
            )

        return account

    async def update_account_async(
        self, account_id: str, **updates
    ) -> Optional[AccountConfig]:
        """Async version of update_account."""
        await self._ensure_connected()

        update_doc = {"updated_at": datetime.utcnow()}

        # Handle API key update
        if "api_key" in updates:
            new_key = updates["api_key"]
            update_doc["api_key"] = new_key
            update_doc["api_key_hash"] = hash_api_key(new_key)

        # Encrypt database URLs if they're being updated
        if "postgres_url" in updates and updates["postgres_url"]:
            updates["postgres_url"] = encrypt_database_url(
                updates["postgres_url"])
        if "mongodb_url" in updates and updates["mongodb_url"]:
            updates["mongodb_url"] = encrypt_database_url(
                updates["mongodb_url"])

        # Add other updates
        allowed_fields = ["name", "postgres_url",
                          "mongodb_url", "gemini_mode", "gemini_api_key"]
        for field in allowed_fields:
            if field in updates and updates[field] is not None:
                update_doc[field] = updates[field]

        result = await self.db.accounts.update_one(
            {"account_id": account_id}, {"$set": update_doc}
        )

        if result.modified_count == 0:
            return None

        # Return updated account
        return await self.get_by_id_async(account_id)

    async def delete_account_async(self, account_id: str) -> bool:
        """Async version of delete_account."""
        await self._ensure_connected()
        result = await self.db.accounts.delete_one({"account_id": account_id})
        return result.deleted_count > 0

    async def rotate_api_key_async(
        self, account_id: str, new_api_key: str
    ) -> Optional[str]:
        """Async version of rotate_api_key."""
        await self._ensure_connected()

        # Get current account to retrieve old key hash
        account_doc = await self.db.accounts.find_one({"account_id": account_id})
        if not account_doc:
            return None

        old_key_hash = account_doc.get("api_key_hash")

        # Update with new key
        await self.db.accounts.update_one(
            {"account_id": account_id},
            {
                "$set": {
                    "api_key": new_api_key,
                    "api_key_hash": hash_api_key(new_api_key),
                    "updated_at": datetime.utcnow(),
                }
            },
        )

        return old_key_hash

    def _doc_to_account(self, doc: Dict) -> AccountConfig:
        """Convert MongoDB document to AccountConfig."""
        return AccountConfig(
            id=doc["account_id"],
            name=doc["name"],
            api_key=doc.get("api_key", ""),
            postgres_url=doc.get("postgres_url", ""),
            mongodb_url=doc.get("mongodb_url", ""),
            gemini_mode=doc.get("gemini_mode", "platform"),
            gemini_api_key=doc.get("gemini_api_key"),
        )


# Global account store instance
# Use MongoDB in production, in-memory for development
account_store: AccountStore = InMemoryAccountStore()


def init_account_store(mongo_url: str, db_name: str = "dbrevel_platform"):
    """Initialize the global account store with MongoDB."""
    global account_store
    account_store = MongoDBAccountStore(mongo_url, db_name)
    return account_store


def get_account_store() -> AccountStore:
    """Get the global account store instance."""
    return account_store


async def verify_account_exists(account_id: str) -> bool:
    """
    Verify that an account exists in the database.

    This is a helper function to check account existence with proper async handling.

    Args:
        account_id: The account ID to verify

    Returns:
        True if account exists, False otherwise
    """
    account = await get_account_store().get_by_id_async(account_id)
    return account is not None
