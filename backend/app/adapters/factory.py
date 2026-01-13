from typing import Dict
import logging

from app.adapters.base import DatabaseAdapter
from app.adapters.mongodb import MongoDBAdapter
from app.adapters.postgres import PostgresAdapter
from app.core.accounts import AccountConfig
from app.core.encryption import decrypt_database_url

logger = logging.getLogger(__name__)


class AdapterFactory:
    """Factory for creating and managing database adapters per account."""

    def __init__(self):
        # account_id -> { db_name -> adapter }
        self._adapters_by_account: Dict[str, Dict[str, DatabaseAdapter]] = {}

    async def _create_adapters_for_account(
        self, account: AccountConfig
    ) -> Dict[str, DatabaseAdapter]:
        """Create and initialize adapters for a specific account.

        Args:
            account: Account configuration

        Returns:
            Dictionary of database adapters (may be empty if all connections fail)

        Raises:
            RuntimeError: If no database adapters could be created for the account
        """

        adapters: Dict[str, DatabaseAdapter] = {}
        errors = []

        # PostgreSQL adapter - decrypt URL before using
        if account.postgres_url:
            try:
                logger.info(f"Initializing PostgreSQL adapter for account {account.id}")
                decrypted_pg_url = decrypt_database_url(account.postgres_url)
                postgres = PostgresAdapter(decrypted_pg_url)
                await postgres.connect()
                await postgres.introspect_schema()
                adapters["postgres"] = postgres
                logger.info(f"✓ PostgreSQL adapter created for account {account.id}")
            except ValueError as e:
                # Decryption or validation error
                error_msg = f"PostgreSQL configuration error for account {account.id}: {e}"
                logger.error(error_msg)
                errors.append(("postgres", "configuration", str(e)))
            except Exception as e:
                # Connection or introspection error
                error_msg = f"Failed to connect to PostgreSQL for account {account.id}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(("postgres", "connection", str(e)))

        # MongoDB adapter - decrypt URL before using
        if account.mongodb_url:
            try:
                logger.info(f"Initializing MongoDB adapter for account {account.id}")
                decrypted_mongo_url = decrypt_database_url(account.mongodb_url)
                # Extract database name from URL
                db_name = decrypted_mongo_url.split("/")[-1].split("?")[0]
                if not db_name:
                    db_name = "dbreveldemo"

                mongodb = MongoDBAdapter(decrypted_mongo_url, db_name)
                await mongodb.connect()
                await mongodb.introspect_schema()
                adapters["mongodb"] = mongodb
                logger.info(f"✓ MongoDB adapter created for account {account.id}")
            except ValueError as e:
                # Decryption or validation error
                error_msg = f"MongoDB configuration error for account {account.id}: {e}"
                logger.error(error_msg)
                errors.append(("mongodb", "configuration", str(e)))
            except Exception as e:
                # Connection or introspection error
                error_msg = f"Failed to connect to MongoDB for account {account.id}: {e}"
                logger.error(error_msg, exc_info=True)
                errors.append(("mongodb", "connection", str(e)))

        # If no adapters were created successfully, raise an error
        if not adapters:
            error_summary = "; ".join([f"{db}: {err}" for db, _, err in errors])
            raise RuntimeError(
                f"Failed to create any database adapters for account {account.id}. "
                f"Errors: {error_summary}"
            )

        # Log warnings if some adapters failed but at least one succeeded
        if errors:
            logger.warning(
                f"Account {account.id} has partial database connectivity. "
                f"Failed: {[db for db, _, _ in errors]}. "
                f"Available: {list(adapters.keys())}"
            )

        return adapters

    async def get_adapters_for_account(
        self, account: AccountConfig
    ) -> Dict[str, DatabaseAdapter]:
        """
        Get (and lazily initialize) adapters for an account.

        This ensures connection pools and schemas are created once per account.
        """

        if account.id not in self._adapters_by_account:
            self._adapters_by_account[account.id] = await self._create_adapters_for_account(
                account
            )

        return self._adapters_by_account[account.id]

    async def shutdown(self):
        """Disconnect all adapters for all accounts."""
        for adapters in self._adapters_by_account.values():
            for adapter in adapters.values():
                await adapter.disconnect()

        self._adapters_by_account.clear()

    async def get(self, account: AccountConfig, name: str) -> DatabaseAdapter:
        """Get adapter by account and database name."""
        adapters = await self.get_adapters_for_account(account)
        if name not in adapters:
            raise ValueError(
                f"No adapter found for database '{name}' for account '{account.id}'")
        return adapters[name]

    async def get_all_schemas(self, account: AccountConfig) -> Dict[str, any]:
        """Get all database schemas for an account."""
        adapters = await self.get_adapters_for_account(account)
        schemas = {}
        for name, adapter in adapters.items():
            # introspect_schema is cached in adapters, so this is cheap after first call
            schemas[name] = await adapter.introspect_schema()
        return schemas


# Singleton instance
adapter_factory = AdapterFactory()
