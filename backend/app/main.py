"""Main FastAPI application

Copyright (c) 2026 Godfrey Samuel
Licensed under the MIT License - see LICENSE file for details

Note: This application requires Python 3.10+ due to google.genai package requirements.
Python 3.10 will stop being supported by Google libraries in October 2026.
Consider upgrading to Python 3.11+ for long-term support.
"""
import logging
import warnings
from contextlib import asynccontextmanager

from app.adapters.factory import adapter_factory
from app.adapters.manager import (get_adapters, set_mongodb_adapter,
                                  set_postgres_adapter)
from app.adapters.mongodb import MongoDBAdapter
from app.adapters.postgres import PostgresAdapter
from app.api.v1.auth import router as auth_router
from app.api.v1.query import router as query_router
from app.api.v1.accounts import router as accounts_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.endpoints.admin import router as admin_router
from app.core.config import settings
from app.core.demo_account import ensure_demo_account
from app.core.email_verification import init_email_verification_store
from app.core.password_reset import init_password_reset_store
from app.core.account_store import init_account_store
from app.core.user_store import init_user_store
from app.core.project_store import initialize_project_store
from app.core.admin_otp import init_admin_otp_store
from app.core.ensure_admin import ensure_admin_user
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Suppress Python version warnings from Google libraries
# These are informational warnings about future deprecation (2026)
warnings.filterwarnings("ignore", category=FutureWarning,
                        module="google.api_core._python_version_support")

logger = logging.getLogger(__name__)


def validate_environment() -> None:
    """Validate required environment variables and security settings on startup

    Raises:
        RuntimeError: If required environment variables are missing or insecure defaults detected
    """
    required_vars = ["GEMINI_API_KEY", "POSTGRES_URL", "MONGODB_URL"]
    missing = []

    for var in required_vars:
        value = getattr(settings, var, None)
        if not value:
            missing.append(var)

    if missing:
        raise RuntimeError(
            f"Missing required environment variables: {', '.join(missing)}. "
            f"Please set them in your .env file or environment."
        )

    # Check for insecure default values in production mode
    if not settings.DEBUG:
        insecure_settings = []

        # Check SECRET_KEY
        if "change-in-production" in settings.SECRET_KEY.lower():
            insecure_settings.append("SECRET_KEY contains default value")

        # Check ENCRYPTION_KEY
        if hasattr(settings, 'ENCRYPTION_KEY'):
            if "your-encryption-key" in settings.ENCRYPTION_KEY.lower():
                insecure_settings.append("ENCRYPTION_KEY contains default value")

        # Check if SECRET_KEY is too short
        if len(settings.SECRET_KEY) < 32:
            insecure_settings.append(f"SECRET_KEY is too short ({len(settings.SECRET_KEY)} chars, minimum 32)")

        if insecure_settings:
            raise RuntimeError(
                f"Insecure configuration detected in production mode:\n" +
                "\n".join(f"  - {issue}" for issue in insecure_settings) +
                "\nPlease update your .env file with secure values."
            )

    logger.info("✓ Environment validation passed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    # Validate environment before starting
    validate_environment()

    # Startup
    pg_adapter = PostgresAdapter(settings.POSTGRES_URL)
    await pg_adapter.connect()
    set_postgres_adapter(pg_adapter)
    print("✓ PostgreSQL connected")

    mongo_db_name = settings.MONGODB_URL.split('/')[-1].split('?')[0]
    mongo_adapter = MongoDBAdapter(settings.MONGODB_URL, mongo_db_name)
    await mongo_adapter.connect()
    set_mongodb_adapter(mongo_adapter)
    print("✓ MongoDB connected")

    await pg_adapter.introspect_schema()
    await mongo_adapter.introspect_schema()
    print("✓ Schemas introspected")

    # Initialize account store with MongoDB for persistence
    # Extract base MongoDB URL (without database name) for account store
    # MONGODB_URL format: mongodb://host:port/database_name
    # We need: mongodb://host:port (base URL) for account store
    if '/' in settings.MONGODB_URL:
        # Split on last '/' to get base URL
        mongo_base_url = '/'.join(settings.MONGODB_URL.rsplit('/', 1)[:-1])
    else:
        mongo_base_url = settings.MONGODB_URL
    init_account_store(mongo_base_url, "dbrevel_platform")
    print("✓ Account store initialized")

    # Initialize user store and password reset store with MongoDB
    init_user_store(mongo_base_url, "dbrevel_platform")
    print("✓ User store initialized")

    init_password_reset_store(mongo_base_url, "dbrevel_platform")
    print("✓ Password reset store initialized")

    init_email_verification_store(mongo_base_url, "dbrevel_platform")
    print("✓ Email verification store initialized")

    # Initialize project store for multi-project support
    initialize_project_store(mongo_base_url, "dbrevel_platform")
    print("✓ Project store initialized")

    # Initialize admin OTP store for admin authentication
    init_admin_otp_store(mongo_base_url, "dbrevel_platform")
    print("✓ Admin OTP store initialized")

    # Ensure demo account exists
    await ensure_demo_account()
    print("✓ Demo account ensured")

    # VERIFY demo project is accessible via API key
    from app.core.demo_account import DEMO_PROJECT_API_KEY, DEMO_PROJECT_ID
    from app.core.project_store import get_project_store

    project_store = get_project_store()
    if project_store:
        demo_project = await project_store.get_by_api_key_async(DEMO_PROJECT_API_KEY)
        if demo_project:
            print(f"✓ Demo project verified: {demo_project.name} is accessible via API key")
        else:
            print(f"⚠️  WARNING: Demo project exists but NOT accessible via API key lookup!")
            print(f"   Demo queries will fail with 'Invalid API key' errors")
            print(f"   Checking MongoDB connection and indexes...")
            # Try to fetch by ID to diagnose
            by_id = await project_store.get_by_id_async(DEMO_PROJECT_ID)
            if by_id:
                print(f"   ✓ Project found by ID: {by_id.name}")
                print(f"   ✗ But lookup by API key fails - check indexes or query logic")
            else:
                print(f"   ✗ Project not found by ID either - was not created!")

    # Ensure default admin user exists
    await ensure_admin_user()

    yield

    # Shutdown
    await pg_adapter.disconnect()
    await mongo_adapter.disconnect()
    await adapter_factory.shutdown()

app = FastAPI(
    title="DbRevel API",
    description="""
## AI-Powered Database SDK

**DBRevel is an AI-powered database SDK that converts natural language into secure, optimized queries for any database. Built on Gemini 3, it eliminates 60% of backend boilerplate—so developers can ship faster, startups can move leaner, and databases become accessible to everyone.**

### Key Features:
* 🤖 **Natural Language Queries** - Just describe what you want
* 🔒 **Security Built-in** - RBAC, validation, and audit trails
* 📊 **Multi-Database** - Works with PostgreSQL and MongoDB
* ⚡ **Fast** - Optimized query generation and execution with caching
* 🏢 **Multi-Tenant SaaS Ready** - Per-tenant databases and Gemini usage

### Authentication

Most endpoints support two authentication methods:

1. **X-Project-Key Header** (API Key Authentication):
   - Add `X-Project-Key: your_project_api_key` to request headers
   - Used for programmatic API access
   - Each project has a unique API key

2. **Demo Project** (Default for Testing):
   - If no `X-Project-Key` header is provided, endpoints automatically use the demo project
   - Demo project includes pre-seeded sample data (ecommerce database)
   - Demo Project Key: `dbrevel_demo_project_key`
   - Perfect for testing and exploring the API

### Demo Data

The demo project includes pre-seeded sample data:
- **PostgreSQL**: `users`, `products`, `orders`, `order_items` tables
- **MongoDB**: `sessions`, `reviews` collections

Try queries like:
- "Get all users"
- "Show products with price over 100"
- "Count orders by status"
- "Get recent reviews"

### Example Query (No Auth Required - Uses Demo Project):
```bash
curl -X POST "http://localhost:8000/api/v1/query" \\
  -H "Content-Type: application/json" \\
  -d '{"intent": "Get all users from Lagos"}'
```

### Example Query (With Project API Key):
```bash
curl -X POST "http://localhost:8000/api/v1/query" \\
  -H "Content-Type: application/json" \\
  -H "X-Project-Key: your_project_api_key" \\
  -d '{"intent": "Show total revenue by product category"}'
```

### Powered by:
* Google Gemini 3 (gemini-2.0-flash-exp)
* FastAPI
* PostgreSQL + MongoDB
    """,
    version="1.0.0",
    contact={
        "name": "Meet the Developer",
        "url": "https://github.com/GodfreySam",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    # License file is in root directory: LICENSE
    lifespan=lifespan,
    # Swagger UI configuration
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,  # Hide schemas section by default
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
    },
)

# CORS Configuration
# Configured to allow requests from frontend and SDK clients
# Supports multiple origins (comma-separated in ALLOWED_ORIGINS env var)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,  # Required for cookies/auth tokens
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    # Allows all headers including X-Project-Key, Authorization, etc.
    allow_headers=["*"],
    expose_headers=["*"],  # Exposes all response headers to clients
    max_age=3600,  # Cache preflight requests for 1 hour
)


@app.get("/")
async def root():
    return {"name": "DbRevel API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    In serverless environments, database connections may not be established yet.
    This endpoint checks connectivity when adapters are available.
    """
    adapters = get_adapters()
    pg_adapter = adapters.get("postgres")
    mongo_adapter = adapters.get("mongodb")

    # In serverless, adapters may not be initialized (lifespan disabled)
    # Check if adapters exist, if not, return "degraded" status
    if not pg_adapter and not mongo_adapter:
        return {
            "status": "degraded",
            "message": "Database adapters not initialized (serverless mode - connections are lazy)",
            "databases": {
                "postgres": "not_initialized",
                "mongodb": "not_initialized"
            }
        }

    pg_healthy = await pg_adapter.health_check() if pg_adapter else False
    mongo_healthy = await mongo_adapter.health_check() if mongo_adapter else False
    return {
        "status": "healthy" if (pg_healthy and mongo_healthy) else "unhealthy",
        "databases": {
            "postgres": "healthy" if pg_healthy else "unhealthy",
            "mongodb": "healthy" if mongo_healthy else "unhealthy"
        }
    }


# Customize OpenAPI schema to remove contact and license from docs (we show them in frontend)
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    # Remove contact and license_info from info section so they don't appear in ReDoc/Swagger
    if "info" in openapi_schema:
        openapi_schema["info"].pop("contact", None)
        openapi_schema["info"].pop("license", None)
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Import router after app creation to avoid circular import

app.include_router(query_router, prefix="/api/v1", tags=["query"])
app.include_router(accounts_router, prefix="/api/v1", tags=["accounts"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(projects_router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
