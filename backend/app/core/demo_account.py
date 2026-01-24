"""Demo project creation and management utilities."""

import os
from typing import Tuple

import app.core.account_store as account_store_module
import asyncpg
from app.core.accounts import AccountConfig
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

# Demo project configuration
DEMO_PROJECT_API_KEY = "dbrevel_demo_project_key"
DEMO_PROJECT_NAME = "Demo Project"
DEMO_PROJECT_ID = "demo_project"
DEMO_ACCOUNT_NAME = "Demo Account"
DEMO_ACCOUNT_ID = "acc_demo_default"

# Demo database names (configurable via env vars)
# These are separate from production databases for safety
# In production, use separate database instances OR different database names
DEMO_POSTGRES_DB = os.getenv("DEMO_POSTGRES_DB", "dbrevel_demo")
DEMO_MONGODB_DB = os.getenv("DEMO_MONGODB_DB", "dbrevel_demo")

# Optional: Add environment suffix for additional isolation
# Set DEMO_ENV_SUFFIX to differentiate local vs production demo databases
# e.g., "_local", "_prod", "_dev"
DEMO_ENV_SUFFIX = os.getenv("DEMO_ENV_SUFFIX", "")


def get_demo_database_urls() -> Tuple[str, str]:
    """
    Get demo database URLs - uses dedicated cloud URLs if configured, otherwise derives from main URLs.

    CONFIGURATION STRATEGY (Priority Order):

    1. **Dedicated Cloud URLs (Recommended - Consistent Across All Environments)**:
       - Set DEMO_POSTGRES_URL and DEMO_MONGODB_URL in .env
       - Points to cloud-hosted databases (PostgreSQL + MongoDB)
       - Same demo data available in local dev, staging, and production
       - Example:
         DEMO_POSTGRES_URL=postgresql://user:pass@host.neon.tech/dbname?sslmode=require
         DEMO_MONGODB_URL=mongodb+srv://user:pass@cluster.mongodb.net/dbrevel_demo

    2. **Derived URLs (Fallback - Environment-Specific)**:
       - If DEMO_*_URL not set, derives from POSTGRES_URL and MONGODB_URL
       - Replaces database name with DEMO_POSTGRES_DB/DEMO_MONGODB_DB
       - Uses local Docker in dev, production DB in prod
       - Optional DEMO_ENV_SUFFIX for additional isolation

    Configuration Variables:
    - DEMO_POSTGRES_URL: Direct PostgreSQL URL for demo (cloud-hosted recommended)
    - DEMO_MONGODB_URL: Direct MongoDB URL for demo (cloud-hosted recommended)
    - DEMO_POSTGRES_DB: Database name when deriving from POSTGRES_URL (default: 'dbrevel_demo')
    - DEMO_MONGODB_DB: Database name when deriving from MONGODB_URL (default: 'dbrevel_demo')
    - DEMO_ENV_SUFFIX: Optional suffix for environment isolation (e.g., '_local', '_prod')

    Returns:
        Tuple of (postgres_demo_url, mongodb_demo_url)
    """
    # Check if dedicated demo URLs are configured (recommended approach)
    if settings.DEMO_POSTGRES_URL and settings.DEMO_MONGODB_URL:
        print(
            "ℹ️  Using dedicated cloud URLs for demo databases (from DEMO_*_URL env vars)"
        )
        return settings.DEMO_POSTGRES_URL, settings.DEMO_MONGODB_URL

    # Fallback: Derive from main database URLs
    print("ℹ️  Deriving demo database URLs from POSTGRES_URL and MONGODB_URL")
    postgres_url = settings.POSTGRES_URL
    mongodb_url = settings.MONGODB_URL

    # Apply environment suffix if configured (e.g., dbrevel_demo_local vs dbrevel_demo_prod)
    # This provides additional isolation when using the same database instance
    pg_db_name = (
        f"{DEMO_POSTGRES_DB}{DEMO_ENV_SUFFIX}" if DEMO_ENV_SUFFIX else DEMO_POSTGRES_DB
    )
    mongo_db_name = (
        f"{DEMO_MONGODB_DB}{DEMO_ENV_SUFFIX}" if DEMO_ENV_SUFFIX else DEMO_MONGODB_DB
    )

    # Construct PostgreSQL demo URL
    if postgres_url.startswith("postgresql://") or postgres_url.startswith(
        "postgres://"
    ):
        # Handle URLs with query parameters
        if "?" in postgres_url:
            base_url, query = postgres_url.split("?", 1)
            # Replace database name in base URL
            parts = base_url.rsplit("/", 1)
            if len(parts) == 2:
                demo_pg_url = f"{parts[0]}/{pg_db_name}?{query}"
            else:
                demo_pg_url = f"{base_url}/{pg_db_name}?{query}"
        else:
            # No query parameters
            parts = postgres_url.rsplit("/", 1)
            if len(parts) == 2:
                demo_pg_url = f"{parts[0]}/{pg_db_name}"
            else:
                demo_pg_url = f"{postgres_url}/{pg_db_name}"
    else:
        demo_pg_url = postgres_url

    # Construct MongoDB demo URL
    # Handle both Docker (mongodb://mongodb:27017/dbrevel_demo) and production URLs
    if mongodb_url.startswith("mongodb://") or mongodb_url.startswith("mongodb+srv://"):
        # Split query parameters if present
        if "?" in mongodb_url:
            base_url, query = mongodb_url.split("?", 1)
            query_str = f"?{query}"
        else:
            base_url = mongodb_url
            query_str = ""

        # Extract base connection string and existing database name
        if "/" in base_url:
            # URL has format: mongodb://host:port/database_name
            parts = base_url.rsplit("/", 1)
            # e.g., "mongodb://mongodb:27017" or "mongodb://localhost:27017"
            connection_string = parts[0]

            # Use demo database name (replace existing if different, or add if missing)
            demo_mongo_url = f"{connection_string}/{mongo_db_name}{query_str}"
        else:
            # URL has format: mongodb://host:port (no database specified)
            demo_mongo_url = f"{base_url}/{mongo_db_name}{query_str}"
    else:
        # Not a standard MongoDB URL, use as-is
        demo_mongo_url = mongodb_url

    return demo_pg_url, demo_mongo_url


async def test_demo_databases(postgres_url: str, mongodb_url: str) -> Tuple[bool, bool]:
    """
    Test if demo databases are accessible.

    Returns:
        Tuple of (postgres_accessible, mongodb_accessible)
    """
    postgres_ok = False
    mongodb_ok = False

    # Test PostgreSQL
    try:
        # Use direct connection (not pooler) for testing
        # Replace pooler port (e.g., 6543) with direct port (5432) if present
        # Works with any connection pooler that uses non-standard ports
        test_url = postgres_url.replace(":6543", ":5432").replace("?pgbouncer=true", "")
        # Disable statement cache for connection pooler compatibility
        conn = await asyncpg.connect(test_url, timeout=5, statement_cache_size=0)
        await conn.execute("SELECT 1")
        await conn.close()
        postgres_ok = True
    except Exception:
        postgres_ok = False

    # Test MongoDB
    try:
        from pymongo import MongoClient

        client: MongoClient = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        client.close()
        mongodb_ok = True
    except Exception:
        mongodb_ok = False

    return postgres_ok, mongodb_ok


async def _seed_demo_mongodb(mongodb_url: str) -> bool:
    """Seed MongoDB demo database with sample data."""
    try:
        import random
        from datetime import datetime, timedelta
        from urllib.parse import urlparse

        # Extract database name from URL
        # URL format: mongodb://host:port/database_name or mongodb://host:port/database_name?query
        parsed = urlparse(mongodb_url)
        db_name = (
            parsed.path.lstrip("/").split("?")[0] if parsed.path else DEMO_MONGODB_DB
        )

        # If no database in URL, use default
        if not db_name:
            db_name = DEMO_MONGODB_DB

        print(
            f"   Connecting to MongoDB database '{db_name}' at {parsed.netloc or 'default'}..."
        )

        # Use motor (async) - MongoDB client will use the database from URL if specified
        client: AsyncIOMotorClient = AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=5000)
        db = client[db_name]

        try:
            # Check if data already exists
            # Use try/except for each count in case collections don't exist yet
            try:
                session_count = await db.sessions.count_documents({})
            except Exception:
                session_count = 0
            try:
                review_count = await db.reviews.count_documents({})
            except Exception:
                review_count = 0
            try:
                order_count = await db.orders.count_documents({})
            except Exception:
                order_count = 0

            # Only seed if databases are empty
            if session_count == 0 and review_count == 0 and order_count == 0:
                # Sessions data
                sessions = []
                for user_id in range(1, 11):
                    for i in range(random.randint(3, 10)):
                        sessions.append(
                            {
                                "user_id": user_id,
                                "started_at": datetime.now()
                                - timedelta(days=random.randint(1, 30)),
                                "ended_at": datetime.now()
                                - timedelta(days=random.randint(0, 29)),
                                "pages_viewed": random.randint(5, 50),
                                "device": random.choice(
                                    ["mobile", "desktop", "tablet"]
                                ),
                                "country": "NG",
                                "city": random.choice(
                                    [
                                        "Lagos",
                                        "Abuja",
                                        "Kano",
                                        "Ibadan",
                                        "Port Harcourt",
                                    ]
                                ),
                            }
                        )

                if sessions:
                    await db.sessions.insert_many(sessions)
                    await db.sessions.create_index("user_id")
                    await db.sessions.create_index("started_at")

                # Reviews data
                reviews = []
                product_ids = list(range(1, 11))
                user_ids = list(range(1, 11))

                review_texts = [
                    "Excellent product! Very satisfied with my purchase.",
                    "Good quality but delivery was a bit slow.",
                    "Amazing! Exactly as described. Will buy again.",
                    "Not bad, but could be better for the price.",
                    "Fantastic! Highly recommend to everyone.",
                    "Product is okay. Nothing special.",
                    "Love it! Best purchase I've made in a while.",
                    "Disappointed. Quality not as expected.",
                    "Great value for money. Very happy!",
                    "Perfect! Exceeded my expectations.",
                ]

                for _ in range(50):
                    reviews.append(
                        {
                            "product_id": random.choice(product_ids),
                            "user_id": random.choice(user_ids),
                            "rating": random.randint(3, 5),
                            "title": f"Review from Customer {random.randint(1, 10)}",
                            "text": random.choice(review_texts),
                            "helpful_count": random.randint(0, 25),
                            "verified_purchase": random.choice(
                                [True, True, True, False]
                            ),
                            "created_at": datetime.now()
                            - timedelta(days=random.randint(1, 60)),
                        }
                    )

                if reviews:
                    await db.reviews.insert_many(reviews)
                    await db.reviews.create_index("product_id")
                    await db.reviews.create_index("user_id")
                    await db.reviews.create_index("rating")

                # Orders data (with status field for demo queries)
                orders = []
                statuses = [
                    "pending",
                    "processing",
                    "shipped",
                    "delivered",
                    "cancelled",
                ]
                for order_id in range(1, 31):
                    orders.append(
                        {
                            "order_id": order_id,
                            "user_id": random.randint(1, 10),
                            "status": random.choice(statuses),
                            "total_amount": round(random.uniform(50.0, 500.0), 2),
                            "items_count": random.randint(1, 5),
                            "created_at": datetime.now()
                            - timedelta(days=random.randint(1, 60)),
                            "updated_at": datetime.now()
                            - timedelta(days=random.randint(0, 59)),
                        }
                    )

                if orders:
                    await db.orders.insert_many(orders)
                    await db.orders.create_index("user_id")
                    await db.orders.create_index("status")
                    await db.orders.create_index("created_at")

                return True
            else:
                return False  # Data already exists
        finally:
            client.close()
    except Exception as e:
        import traceback

        print(f"⚠️  Error in _seed_demo_mongodb: {e}")
        print(f"   Traceback: {traceback.format_exc()}")
        return False


def _truncate_error_message(error: Exception, max_length: int = 200) -> str:
    """Truncate long error messages to keep logs clean."""
    error_str = str(error)
    # Remove verbose DNS resolution details
    if (
        "DNS operation timed out" in error_str
        or "resolution lifetime expired" in error_str
    ):
        # Extract just the main error before DNS details
        if ":" in error_str:
            error_str = error_str.split(":")[0] + ": DNS resolution timeout"
    # Remove verbose topology descriptions from MongoDB errors
    if "Topology Description" in error_str:
        parts = error_str.split("Topology Description")
        if parts:
            error_str = parts[0].strip()

    # Truncate if still too long
    if len(error_str) > max_length:
        error_str = error_str[:max_length] + "..."

    return error_str


async def ensure_demo_account() -> bool:
    """
    Ensure demo account and demo project exist and are configured correctly.

    This function:
    1. Checks if demo databases are accessible
    2. Creates or updates demo account if needed (parent account for demo project)
    3. Creates or updates demo project with API key
    4. Seeds demo data if databases are empty
    5. Returns True if demo project is available, False otherwise

    Returns:
        True if demo account and project were created/updated successfully, False otherwise
    """
    # Check if demo account creation is enabled
    demo_enabled = os.getenv("DEMO_ACCOUNT_ENABLED", "true").lower() == "true"
    if not demo_enabled:
        return False

    try:
        # Get demo database URLs
        demo_pg_url, demo_mongo_url = get_demo_database_urls()

        # Test if demo databases are accessible (non-blocking, just for info)
        pg_ok, mongo_ok = await test_demo_databases(demo_pg_url, demo_mongo_url)

        # Note: We'll still try to create/update account and seed data even if test fails
        # MongoDB creates databases on first write, so seeding can succeed even if test fails

        # Step 1: Ensure demo account exists (parent account for demo project)
        # Get current account store instance
        account_store = account_store_module.account_store
        existing_account = await account_store.get_by_id_async(DEMO_ACCOUNT_ID)

        if not existing_account:
            # Create new demo account (parent for demo project)
            # Note: Demo account doesn't need an API key since projects have the keys
            await account_store.create_account_async(
                name=DEMO_ACCOUNT_NAME,
                api_key="",  # No account-level API key needed
                postgres_url="",  # Projects have their own DB URLs
                mongodb_url="",
                gemini_mode="platform",
                gemini_api_key=None,
                account_id=DEMO_ACCOUNT_ID,  # Always use "acc_demo_default" as the ID
            )
            print(
                f"✓ Demo account created: {DEMO_ACCOUNT_NAME} (ID: {DEMO_ACCOUNT_ID})"
            )

        # Step 2: Ensure demo project exists under demo account
        from app.core.project_store import get_project_store

        project_store = get_project_store()
        if not project_store:
            print(
                "⚠️  Warning: Project store not initialized, skipping demo project creation"
            )
            print("   Demo project will be created on first use if needed")
            return True  # Don't fail - allow server to start

        existing_project = await project_store.get_by_id_async(DEMO_PROJECT_ID)

        if existing_project:
            # Update existing project with current demo database URLs and account_id
            # (This ensures account_id stays in sync if constant changes)
            await project_store.update_project_async(
                DEMO_PROJECT_ID,
                account_id=DEMO_ACCOUNT_ID,  # Ensure account_id is always current
                postgres_url=demo_pg_url,
                mongodb_url=demo_mongo_url,
            )
            print(
                f"✓ Demo project updated: {DEMO_PROJECT_NAME} (API Key: {DEMO_PROJECT_API_KEY[:20]}...)"
            )
        else:
            # Create new demo project
            await project_store.create_project_async(
                name=DEMO_PROJECT_NAME,
                account_id=DEMO_ACCOUNT_ID,
                api_key=DEMO_PROJECT_API_KEY,
                postgres_url=demo_pg_url,
                mongodb_url=demo_mongo_url,
                project_id=DEMO_PROJECT_ID,
            )
            print(
                f"✓ Demo project created: {DEMO_PROJECT_NAME} (ID: {DEMO_PROJECT_ID}, API Key: {DEMO_PROJECT_API_KEY[:20]}...)"
            )

        # VERIFY it was stored correctly and is accessible via API key lookup
        verification = await project_store.get_by_api_key_async(DEMO_PROJECT_API_KEY)
        if verification:
            print("  ✓ Verified: Demo project is accessible via API key lookup")
        else:
            print(
                "  ⚠️  WARNING: Demo project created but NOT accessible via API key lookup!"
            )
            print("     This will cause 'Invalid API key' errors for demo queries")
            # Diagnose the issue
            by_id = await project_store.get_by_id_async(DEMO_PROJECT_ID)
            if by_id:
                print(f"     Project exists in DB with ID: {by_id.id}")
                print(f"     Stored API key: {by_id.api_key[:20]}...")
                print(f"     Is active: {by_id.is_active}")
            else:
                print("     Project not found by ID either - creation failed!")

        # Get the final project's MongoDB URL for seeding
        final_project = await project_store.get_by_id_async(DEMO_PROJECT_ID)
        tenant_mongo_url = demo_mongo_url  # Default to constructed URL
        if final_project and final_project.mongodb_url:
            tenant_mongo_url = final_project.mongodb_url
            print("   Using project's configured MongoDB URL for seeding")

        # Always try to seed MongoDB demo data (database will be created on first write if it doesn't exist)
        # Only seed if the database is empty to avoid overwriting existing data
        # Try seeding even if test_demo_databases failed (database might not exist yet)
        print("🌱 Checking and seeding demo MongoDB database...")
        try:
            # Decrypt the MongoDB URL before using it (tenant store encrypts URLs for security)
            from app.core.encryption import decrypt_database_url

            try:
                decrypted_mongo_url = decrypt_database_url(tenant_mongo_url)
            except Exception as decrypt_error:
                # If decryption fails, the URL might already be plaintext (for backward compatibility)
                # or there might be an encryption key issue
                if tenant_mongo_url.startswith(("mongodb://", "mongodb+srv://")):
                    # Already plaintext, use as-is
                    decrypted_mongo_url = tenant_mongo_url
                    print("   Using plaintext MongoDB URL (decryption skipped)")
                else:
                    raise ValueError(f"Failed to decrypt MongoDB URL: {decrypt_error}")

            seeded = await _seed_demo_mongodb(decrypted_mongo_url)
            if seeded:
                print("✓ Seeded demo MongoDB database with sample data")
            else:
                print("ℹ️  Demo MongoDB database already contains data (skipping seed)")
        except Exception as e:
            import traceback

            error_msg = _truncate_error_message(e)
            print(f"⚠️  Warning: Could not seed demo MongoDB: {error_msg}")
            # Don't print full traceback for DNS/connection errors - too verbose
            if "DNS" not in str(e) and "Topology" not in str(e):
                print(f"   Traceback: {traceback.format_exc()}")

        return True

    except Exception as e:
        # Non-blocking: log warning but don't fail startup
        error_msg = _truncate_error_message(e)
        print(f"⚠️  Warning: Could not create/update demo account: {error_msg}")
        return False


def get_demo_account_config() -> AccountConfig:
    """
    Get the AccountConfig for the demo account.

    This is used to pre-warm the demo account adapters at startup and for health checks.
    """
    postgres_url, mongodb_url = get_demo_database_urls()
    return AccountConfig(
        id=DEMO_ACCOUNT_ID,
        name=DEMO_ACCOUNT_NAME,
        api_key=DEMO_PROJECT_API_KEY,
        postgres_url=postgres_url,
        mongodb_url=mongodb_url,
        gemini_mode="platform",
        gemini_api_key=None,
    )
