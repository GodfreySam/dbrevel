"""
This module defines the `AdapterFactory`, a centralized factory for creating,
managing, and caching database adapters for different accounts.

The factory is responsible for:
- Lazily initializing database adapters (e.g., PostgreSQL, MongoDB) on a per-account basis.
- Handling database URL decryption and secure connection setup.
- Gracefully managing partial database connectivity, allowing the application to
  function even if one of an account's databases is unavailable.
- Providing a singleton instance (`adapter_factory`) for global access.
"""

import asyncio
import logging
from typing import Dict

from app.adapters.base import DatabaseAdapter
from app.adapters.mongodb import MongoDBAdapter
from app.adapters.postgres import PostgresAdapter
from app.core.accounts import AccountConfig
from app.core.encryption import decrypt_database_url

logger = logging.getLogger(__name__)


class AdapterFactory:
    """
    A factory for creating and managing database adapters on a per-account basis.

    This class uses a lazy initialization strategy, creating and caching adapters
    only when they are first requested for an account. This avoids unnecessary
    database connections for inactive accounts.
    """

    def __init__(self):
        """Initializes the AdapterFactory with an empty cache for adapters."""
        # A nested dictionary to store adapters: {account_id: {db_name: adapter}}
        self._adapters_by_account: Dict[str, Dict[str, DatabaseAdapter]] = {}

    async def _create_adapters_for_account(
        self, account: AccountConfig
    ) -> Dict[str, DatabaseAdapter]:
        """
        Creates and initializes all configured database adapters for a specific account.

        This method attempts to connect to each database specified in the account
        configuration (e.g., PostgreSQL, MongoDB). It handles connection errors
        gracefully, allowing the application to proceed with partial connectivity.

        Args:
            account: The configuration for the account.

        Returns:
            A dictionary of successfully initialized database adapters, keyed by database name.

        Raises:
            RuntimeError: If no database adapters could be successfully created for the account.
        """
        adapters: Dict[str, DatabaseAdapter] = {}
        errors = []

        # PostgreSQL adapter - decrypt URL before using
        # Use "postgres" as the adapter key so Gemini query plans (database: "postgres") match.
        if account.postgres_url:
            pg_adapter_key = "postgres"
            try:
                logger.info(
                    f"Initializing PostgreSQL adapter for account {account.id}")
                decrypted_pg_url = decrypt_database_url(account.postgres_url)
                pg_db_name = decrypted_pg_url.split("/")[-1].split("?")[0]
                postgres = PostgresAdapter(decrypted_pg_url)
                await postgres.connect()
                adapters[pg_adapter_key] = postgres
                logger.info(
                    f"✓ PostgreSQL adapter created for account {account.id} (key: {pg_adapter_key}, actual db: {pg_db_name})"
                )
            except (asyncio.TimeoutError, TimeoutError) as e:
                error_msg = (
                    f"Connection timed out for PostgreSQL (Account {account.id})"
                )
                logger.warning(error_msg)
                errors.append((pg_adapter_key, "timeout", str(e)))
            except ValueError as e:
                error_msg = (
                    f"PostgreSQL configuration error for account {account.id}: {e}"
                )
                logger.error(error_msg)
                errors.append((pg_adapter_key, "configuration", str(e)))
            except Exception as e:
                error_msg = f"Failed to initialize PostgreSQL adapter for account {account.id}: {e}"
                logger.warning(error_msg, exc_info=True)
                errors.append((pg_adapter_key, "connection", str(e)))

        # MongoDB adapter - decrypt URL before using
        if account.mongodb_url:
            # Always use 'mongodb' as the key for the MongoDB adapter
            # This ensures consistency with how queries might reference the MongoDB database
            mongo_adapter_key = "mongodb"
            try:
                logger.info(
                    f"Initializing MongoDB adapter for account {account.id}")
                decrypted_mongo_url = decrypt_database_url(account.mongodb_url)
                # The actual database name from the URL might be different,
                # but for consistency with query plans, we'll use "mongodb" as the key.
                # The MongoDBAdapter constructor still needs the actual db_name for connection.
                db_name_from_url = decrypted_mongo_url.split(
                    "/")[-1].split("?")[0]
                if not db_name_from_url:
                    db_name_from_url = "dbrevel_demo"  # Fallback if no db name in URL

                mongodb = MongoDBAdapter(decrypted_mongo_url, db_name_from_url)
                await mongodb.connect()
                # Don't introspect schema during startup - do it lazily when needed
                # This speeds up startup and avoids connection issues
                adapters[mongo_adapter_key] = mongodb
                logger.info(
                    f"✓ MongoDB adapter created for account {account.id} (key: {mongo_adapter_key}, actual db: {db_name_from_url})"
                )
            except (asyncio.TimeoutError, TimeoutError) as e:
                error_msg = f"Connection timed out for MongoDB (Account {account.id})"
                logger.warning(error_msg)
                errors.append((mongo_adapter_key, "timeout", str(e)))
            except ValueError as e:
                error_msg = f"MongoDB configuration error for account {account.id}: {e}"
                logger.error(error_msg)
                errors.append((mongo_adapter_key, "configuration", str(e)))
            except Exception as e:
                error_msg = f"Failed to initialize MongoDB adapter for account {account.id}: {e}"
                logger.warning(error_msg, exc_info=True)
                errors.append((mongo_adapter_key, "connection", str(e)))

        # If no adapters were created successfully, raise an error
        if not adapters:
            error_summary = "; ".join(
                [f"{db}: {err}" for db, _, err in errors])
            raise RuntimeError(
                f"Failed to create any database adapters for account {account.id}. "
                f"Errors: {error_summary}"
            )

        # Log warnings if some adapters failed but at least one succeeded
        if errors:
            failed_dbs = [db for db, _, _ in errors]
            logger.warning(
                f"Account {account.id} has partial database connectivity. "
                f"Failed: {failed_dbs}. "
                f"Available: {list(adapters.keys())}"
            )

        return adapters

    async def get_adapters_for_account(
        self, account: AccountConfig
    ) -> Dict[str, DatabaseAdapter]:
        """
        Retrieves (and lazily initializes) the database adapters for a given account.

        This method ensures that connection pools and schema introspection are performed
        only once per account. The results are cached for subsequent calls.

        Args:
            account: The account for which to retrieve adapters.

        Returns:
            A dictionary of database adapters available for the account.
        """
        if account.id not in self._adapters_by_account:
            self._adapters_by_account[
                account.id
            ] = await self._create_adapters_for_account(account)

        return self._adapters_by_account[account.id]

    async def shutdown(self):
        """
        Disconnects all active adapters for all accounts and clears the cache.

        This should be called during application shutdown to ensure graceful
        termination of all database connections.
        """
        import asyncio
        logger.info(f"Shutting down {len(self._adapters_by_account)} account(s) with adapters...")
        
        # Disconnect all adapters in parallel with timeout protection
        disconnect_tasks = []
        for account_id, adapters in self._adapters_by_account.items():
            for db_name, adapter in adapters.items():
                task = asyncio.create_task(adapter.disconnect())
                disconnect_tasks.append((account_id, db_name, task))
        
        # Wait for all disconnects with timeout
        for account_id, db_name, task in disconnect_tasks:
            try:
                await asyncio.wait_for(task, timeout=2.0)
                logger.debug(f"Disconnected {db_name} for account {account_id}")
            except asyncio.TimeoutError:
                logger.warning(f"Timeout disconnecting {db_name} for account {account_id}")
            except Exception as e:
                logger.error(f"Error disconnecting {db_name} for account {account_id}: {e}")

        self._adapters_by_account.clear()
        logger.info("Adapter factory shutdown complete")

    async def get(self, account: AccountConfig, name: str) -> DatabaseAdapter:
        """
        Retrieves a specific database adapter for an account by name.

        Args:
            account: The account for which to retrieve the adapter.
            name: The name of the database adapter (e.g., 'postgres', 'dbrevel_demo').

        Returns:
            The requested `DatabaseAdapter` instance.

        Raises:
            ValueError: If no adapter with the given name is found for the account.
        """
        adapters = await self.get_adapters_for_account(account)
        if name not in adapters:
            raise ValueError(
                f"No adapter found for database '{name}' for account '{account.id}'"
            )
        return adapters[name]

    async def get_all_schemas(self, account: AccountConfig) -> Dict[str, any]:
        """
        Retrieves the database schemas for all available adapters for an account.

        The schema introspection is cached within each adapter, so this operation
        is inexpensive after the first call.

        Args:
            account: The account for which to retrieve schemas.

        Returns:
            A dictionary mapping database names to their schema objects.
        """
        adapters = await self.get_adapters_for_account(account)
        schemas = {}
        for name, adapter in adapters.items():
            schemas[name] = await adapter.introspect_schema()
        return schemas


# Singleton instance of the factory for global use.
adapter_factory = AdapterFactory()
