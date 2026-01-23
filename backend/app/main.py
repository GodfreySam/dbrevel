"""Main FastAPI application

Copyright (c) 2026 Godfrey Samuel
Licensed under the MIT License - see LICENSE file for details

Note: This application requires Python 3.10+ due to google.genai package requirements.
Python 3.10 will stop being supported by Google libraries in October 2026.
Consider upgrading to Python 3.11+ for long-term support.
"""
import asyncio
import logging
import warnings
from contextlib import asynccontextmanager

from app.adapters.factory import adapter_factory
from app.api.error_handlers import add_exception_handlers
from app.api.v1.accounts import router as accounts_router
from app.api.v1.auth import router as auth_router
from app.api.v1.endpoints.admin import router as admin_router
from app.api.v1.endpoints.projects import router as projects_router
from app.api.v1.query import router as query_router
from app.api.v1.schema import router as schema_router
from app.core.account_store import init_account_store
from app.core.admin_otp import init_admin_otp_store
from app.core.config import settings
from app.core.demo_account import ensure_demo_account, get_demo_account_config
from app.core.email_verification import init_email_verification_store
from app.core.ensure_admin import ensure_admin_user
from app.core.password_reset import init_password_reset_store
from app.core.project_store import initialize_project_store
from app.core.user_store import init_user_store
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
                insecure_settings.append(
                    "ENCRYPTION_KEY contains default value")

        # Check if SECRET_KEY is too short
        if len(settings.SECRET_KEY) < 32:
            insecure_settings.append(
                f"SECRET_KEY is too short ({len(settings.SECRET_KEY)} chars, minimum 32)")

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
    # Suppress pymongo background reconnection errors (these are periodic tasks that shouldn't clutter logs)
    # These errors occur when MongoDB Atlas shards are unreachable but don't affect active connections
    logging.getLogger("pymongo.synchronous.pool").setLevel(logging.ERROR)
    logging.getLogger(
        "pymongo.synchronous.mongo_client").setLevel(logging.ERROR)

    # Validate environment before starting
    validate_environment()

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

    # Ensure demo account and project exist, and seed data if needed
    demo_ok = await ensure_demo_account()
    if demo_ok:
        print("✓ Demo account ensured")
    else:
        print("⚠️  Demo account setup skipped or failed (MongoDB may be unreachable)")

    # Pre-warm demo account adapters (non-blocking - don't fail startup if this fails)
    # Schema introspection is now lazy, so this just establishes connections
    demo_config = get_demo_account_config()
    try:
        # Use asyncio.wait_for to prevent hanging on slow connections
        await asyncio.wait_for(
            adapter_factory.get_adapters_for_account(demo_config),
            timeout=15.0  # 15 second timeout for pre-warming
        )
        print("✓ Demo account database adapters pre-warmed")
    except asyncio.TimeoutError:
        print("⚠️  Warning: Demo account adapter pre-warming timed out (connections will be established on-demand)")
    except Exception as e:
        print(f"⚠️  Warning: Could not pre-warm demo account adapters: {e}")
        print("   Connections will be established on-demand when needed")

    # VERIFY demo project is accessible via API key (non-blocking - don't fail startup)
    try:
        from app.core.demo_account import DEMO_PROJECT_API_KEY, DEMO_PROJECT_ID
        from app.core.project_store import get_project_store

        project_store = get_project_store()
        if project_store:
            demo_project = await project_store.get_by_api_key_async(DEMO_PROJECT_API_KEY)
            if demo_project:
                print(
                    f"✓ Demo project verified: {demo_project.name} is accessible via API key")
            else:
                print(
                    f"⚠️  WARNING: Demo project exists but NOT accessible via API key lookup!")
                print(f"   Demo queries will fail with 'Invalid API key' errors")
                print(f"   Checking MongoDB connection and indexes...")
                by_id = await project_store.get_by_id_async(DEMO_PROJECT_ID)
                if by_id:
                    print(f"   ✓ Project found by ID: {by_id.name}")
                    print(f"   ✗ But lookup by API key fails - check indexes or query logic")
                else:
                    print(f"   ✗ Project not found by ID either - was not created!")
    except Exception as e:
        logger.warning(
            "Could not verify demo project (MongoDB may be unreachable): %s. "
            "Demo queries will fail until MongoDB is available.", e
        )

    # Ensure default admin user exists (non-blocking - don't fail startup)
    try:
        await ensure_admin_user()
    except Exception as e:
        logger.warning(
            "Could not ensure admin user (MongoDB may be unreachable): %s. "
            "Admin login will fail until MongoDB is available.", e
        )

    yield

    # Shutdown
    await adapter_factory.shutdown()

app = FastAPI(
    title="DbRevel API",
    description="""
## AI-Powered Database SDK

**DbRevel is an AI-powered database SDK that converts natural language into secure, optimized queries for any database. Designed with scalability in mind, it supports multiple AI models and eliminates 60% of backend boilerplate—so developers can ship faster, startups can move leaner, and databases become accessible to everyone.**

### Quick Start

**1. Install the SDK:**
```bash
npm install @dbrevel/sdk
```

**2. Use the SDK:**
```typescript
import { DbRevelClient } from '@dbrevel/sdk';

const client = new DbRevelClient({
  baseUrl: 'https://api.dbrevel.io',
  apiKey: 'dbrevel_demo_project_key', // Use demo key for testing
});

const result = await client.query("Get all users");
console.log(result.data);
```

**3. Or use the REST API directly:**
```bash
curl -X POST "https://api.dbrevel.io/api/v1/query" \\
  -H "Content-Type: application/json" \\
  -H "X-Project-Key: dbrevel_demo_project_key" \\
  -d '{"intent": "Get all users"}'
```

### Authentication

**API Key Authentication (Recommended):**
- Add `X-Project-Key: your_project_api_key` header to requests
- Get your API key from the [dashboard](https://dbrevel.io/dashboard) after creating a project
- For testing, use the demo key: `dbrevel_demo_project_key`

**Demo Project (No Auth Required):**
- Leave `X-Project-Key` header empty to automatically use the demo project
- Demo project includes pre-seeded sample data (users, products, orders, reviews)
- Perfect for exploring the API!

### Demo Data

The demo project includes pre-seeded sample data:
- **PostgreSQL**: `users`, `products`, `orders`, `order_items` tables
- **MongoDB**: `sessions`, `reviews` collections

**Try these queries:**
- "Get all users"
- "Show products with price over 100"
- "Count orders by status"
- "Get customers in Lagos with more than 5 orders"
- "Get recent reviews"

### Features

* 🤖 **Natural Language Queries** - Just describe what you want
* 🔒 **Security Built-in** - Query validation, RBAC, and audit trails
* 📊 **Multi-Database** - Works with PostgreSQL and MongoDB
* ⚡ **Fast** - Optimized query generation and execution
* 🏢 **Multi-Tenant SaaS Ready** - Per-project database isolation

### Resources

* **SDK Documentation**: [npmjs.com/package/@dbrevel/sdk](https://www.npmjs.com/package/@dbrevel/sdk)
* **Dashboard**: [dbrevel.io/dashboard](https://dbrevel.io/dashboard)
* **Website**: [dbrevel.io](https://dbrevel.io)

### Powered by

* AI Models (scalable architecture supporting multiple providers)
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
        "persistAuthorization": True,  # Remember auth settings
        "defaultModelExpandDepth": 1,  # Show one level of models by default
    },
)

# Add custom exception handlers
add_exception_handlers(app)

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
async def shallow_health_check():
    """
    Shallow health check to confirm the API is running.
    Returns a 200 OK response without checking database connections.
    """
    return {"status": "healthy"}


@app.get("/health/deep")
async def deep_health_check():
    """
    Health check endpoint for the demo environment.
    This checks the connectivity of the pre-warmed demo database adapters.
    """
    try:
        demo_config = get_demo_account_config()
        adapters = await adapter_factory.get_adapters_for_account(demo_config)

        pg_adapter = adapters.get("postgres")
        mongo_adapter = adapters.get("mongodb")

        if not pg_adapter and not mongo_adapter:
            return {
                "status": "degraded",
                "message": "Demo database adapters not found in factory.",
                "databases": {
                    "postgres": "not_initialized",
                    "mongodb": "not_initialized"
                }
            }

        pg_healthy = await pg_adapter.health_check() if pg_adapter else False
        mongo_healthy = await mongo_adapter.health_check() if mongo_adapter else False

        return {
            "status": "healthy" if pg_healthy and mongo_healthy else "unhealthy",
            "databases": {
                "postgres": "healthy" if pg_healthy else "unhealthy",
                "mongodb": "healthy" if mongo_healthy else "unhealthy"
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "message": "An error occurred during health check.",
            "error": str(e)
        }


# Customize OpenAPI schema to remove contact and license from docs (we show them in frontend)
# Also filter out dashboard/admin endpoints - only show SDK/API endpoints
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from app.core.demo_account import DEMO_PROJECT_API_KEY
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

    # Filter out dashboard/admin/auth endpoints - only keep SDK/API endpoints
    # Keep: /api/v1/query, /api/v1/schema/*
    # Remove: /api/v1/auth/*, /api/v1/accounts/*, /api/v1/projects/*, /api/v1/admin/*
    if "paths" in openapi_schema:
        filtered_paths = {}
        for path, methods in openapi_schema["paths"].items():
            # Keep query endpoint
            if path == "/api/v1/query":
                # Ensure examples are at content level for Swagger UI
                if "post" in methods:
                    post_method = methods["post"]
                    request_body = post_method.get("requestBody", {})
                    if request_body and "content" in request_body:
                        content = request_body["content"]
                        if "application/json" in content:
                            json_content = content["application/json"]
                            schema = json_content.get("schema", {})
                            # Move examples from schema to content level if they exist
                            if "examples" in schema:
                                json_content["examples"] = schema.pop(
                                    "examples")
                            elif "$ref" in schema:
                                # Check if examples are in the referenced schema component
                                ref_path = schema["$ref"].replace(
                                    "#/components/schemas/", "")
                                if ref_path in openapi_schema.get("components", {}).get("schemas", {}):
                                    ref_schema = openapi_schema["components"]["schemas"][ref_path]
                                    if "examples" in ref_schema:
                                        json_content["examples"] = ref_schema.pop(
                                            "examples")
                filtered_paths[path] = methods
            # Keep schema endpoints
            elif path.startswith("/api/v1/schema"):
                filtered_paths[path] = methods
            # Keep health check
            elif path == "/health" or path == "/":
                filtered_paths[path] = methods
            # Remove all other endpoints (auth, accounts, projects, admin)
            # These are for dashboard use, not SDK/API users
        openapi_schema["paths"] = filtered_paths

    # Add security scheme for X-Project-Key header with demo key as default
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    if "securitySchemes" not in openapi_schema["components"]:
        openapi_schema["components"]["securitySchemes"] = {}

    # Define API key security scheme
    openapi_schema["components"]["securitySchemes"]["ProjectApiKey"] = {
        "type": "apiKey",
        "name": "X-Project-Key",
        "in": "header",
        "description": f"Project API key for authentication. Use `{DEMO_PROJECT_API_KEY}` for demo/testing with pre-seeded sample data. Get your own API key from the dashboard after creating a project.",
        "x-default": DEMO_PROJECT_API_KEY  # Pre-fill with demo key in Swagger UI
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# Import router after app creation to avoid circular import

app.include_router(query_router, prefix="/api/v1", tags=["query"])
app.include_router(schema_router, prefix="/api/v1", tags=["schema"])
app.include_router(accounts_router, prefix="/api/v1", tags=["accounts"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(
    projects_router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
