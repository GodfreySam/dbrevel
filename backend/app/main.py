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

import sentry_sdk
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
from app.core.metrics import PrometheusMiddleware, get_metrics_response
from app.core.password_reset import init_password_reset_store
from app.core.project_store import initialize_project_store
from app.core.rate_limit import limiter
from app.core.user_store import init_user_store
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


def safe_rate_limit_handler(request: Request, exc: Exception):
    """Safe rate limit handler that handles both RateLimitExceeded and other exceptions."""
    from fastapi.responses import JSONResponse
    from slowapi import _rate_limit_exceeded_handler
    if isinstance(exc, RateLimitExceeded):
        # Use the standard handler for RateLimitExceeded
        return _rate_limit_exceeded_handler(request, exc)
    else:
        # For other exceptions (like ConnectionError), return a generic error
        return JSONResponse(
            status_code=429,
            content={"error": f"Rate limit exceeded: {str(exc)}"}
        )


def safe_rate_limit_handler(request: Request, exc: Exception):
    """Safe rate limit handler that handles both RateLimitExceeded and other exceptions."""
    from fastapi.responses import JSONResponse
    if isinstance(exc, RateLimitExceeded):
        # Use the standard handler for RateLimitExceeded
        return _rate_limit_exceeded_handler(request, exc)
    else:
        # For other exceptions (like ConnectionError), return a generic error
        return JSONResponse(
            status_code=429,
            content={"error": f"Rate limit exceeded: {str(exc)}"}
        )

# Suppress Python version warnings from Google libraries
# These are informational warnings about future deprecation (2026)
warnings.filterwarnings("ignore", category=FutureWarning,
                        module="google.api_core._python_version_support")

logger = logging.getLogger(__name__)


class _StderrFilter:
    """Filter stderr to suppress MongoDB background reconnection errors."""

    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
        self.buffer = []
        self.max_buffer_lines = 30  # Max lines to buffer for a traceback

    def write(self, text):
        """Write to stderr, filtering MongoDB background errors."""
        if not text:
            return

        # Add to buffer
        self.buffer.append(text)

        # Get full buffer content
        buffer_text = "".join(self.buffer)

        # Check for MongoDB background error signature (plan: Key Patterns to Filter)
        # Traceback: _process_periodic_tasks, update_pool, remove_stale_sockets, pymongo/synchronous/
        # Exception: AutoReconnect, gaierror, nodename nor servname provided
        has_mongodb_traceback = (
            "_process_periodic_tasks" in buffer_text
            or "pymongo/synchronous/" in buffer_text
            or (
                "pymongo.synchronous" in buffer_text
                and (
                    "update_pool" in buffer_text
                    or "remove_stale_sockets" in buffer_text
                    or "pymongo.synchronous.pool" in buffer_text
                    or "pymongo.synchronous.mongo_client" in buffer_text
                )
            )
        )

        has_mongodb_exception = (
            "pymongo.errors.AutoReconnect:" in buffer_text
            or "pymongo.errors.ServerSelectionTimeoutError:" in buffer_text
            or (
                ("socket.gaierror:" in buffer_text or "gaierror:" in buffer_text)
                and "nodename nor servname provided" in buffer_text
            )
        )

        # If we detect a complete MongoDB background error traceback, suppress it
        if has_mongodb_traceback and has_mongodb_exception:
            self.buffer.clear()
            return

        # If buffer gets too large or we see a clear non-MongoDB pattern, flush
        if len(self.buffer) > self.max_buffer_lines:
            if not has_mongodb_traceback:
                self._flush()
            elif len(self.buffer) > self.max_buffer_lines * 2:
                self._flush()

        # Flush on newline if we're confident it's not MongoDB-related
        if "\n" in text and not has_mongodb_traceback and len(self.buffer) > 1:
            self._flush()

    def _flush(self):
        """Flush buffer to original stderr."""
        if self.buffer:
            self.original_stderr.write("".join(self.buffer))
            self.buffer.clear()

    def flush(self):
        """Flush method required by file-like interface."""
        self._flush()
        self.original_stderr.flush()

    def __getattr__(self, name):
        """Delegate other attributes to original stderr."""
        return getattr(self.original_stderr, name)


# Store original stderr for restoration if needed (plan: Install Stderr Filter Early)
_original_stderr = None


def _install_stderr_filter():
    """Install stderr filter to suppress MongoDB background errors."""
    import sys
    global _original_stderr
    if not isinstance(sys.stderr, _StderrFilter):
        _original_stderr = sys.stderr
        sys.stderr = _StderrFilter(_original_stderr)
        logger.debug(
            "Installed stderr filter for MongoDB background error suppression")


def _suppress_mongodb_background_errors():
    """Suppress MongoDB background reconnection errors that clutter logs."""
    import sys
    import threading
    import traceback

    # Store original exception handlers
    original_excepthook = sys.excepthook

    def is_mongodb_background_error(exc_type, exc_value, exc_traceback):
        """Check if this is a MongoDB background reconnection error."""
        if exc_type is None:
            return False

        error_str = str(exc_value) if exc_value else ""
        error_type_name = exc_type.__name__ if exc_type else ""
        exc_module = getattr(exc_type, "__module__", "") or ""

        # Format traceback safely (plan: handle edge cases where traceback might be None)
        try:
            traceback_str = (
                "".join(traceback.format_tb(exc_traceback))
                if exc_traceback is not None
                else ""
            )
        except Exception:
            traceback_str = ""

        # Check for MongoDB background reconnection patterns (plan: gaierror, better traceback matching)
        # Exception types: AutoReconnect, ServerSelectionTimeoutError, gaierror (DNS errors)
        is_mongodb_exception_type = (
            error_type_name in ("AutoReconnect", "ServerSelectionTimeoutError")
            or (error_type_name == "gaierror" and exc_module == "socket")
        )

        # Traceback patterns: _process_periodic_tasks, update_pool, remove_stale_sockets,
        # pymongo/synchronous/, pymongo.synchronous.pool, pymongo.synchronous.mongo_client
        has_mongodb_traceback = (
            "_process_periodic_tasks" in traceback_str
            or "update_pool" in traceback_str
            or "remove_stale_sockets" in traceback_str
            or "pymongo/synchronous/" in traceback_str
            or "pymongo.synchronous.pool" in traceback_str
            or "pymongo.synchronous.mongo_client" in traceback_str
        )

        # Also match "nodename nor servname provided" (DNS resolution failure)
        has_dns_error = "nodename nor servname provided" in error_str

        is_mongodb_error = is_mongodb_exception_type and (
            has_mongodb_traceback or has_dns_error
        )

        return is_mongodb_error

    def custom_excepthook(exc_type, exc_value, exc_traceback):
        """Custom exception handler that suppresses MongoDB background errors."""
        if not is_mongodb_background_error(exc_type, exc_value, exc_traceback):
            # For all other exceptions, use the original handler
            original_excepthook(exc_type, exc_value, exc_traceback)
        # Otherwise, silently suppress MongoDB background errors

    # Install custom exception handler for main thread
    sys.excepthook = custom_excepthook

    # Install custom exception handler for background threads (Python 3.8+)
    if hasattr(threading, 'excepthook'):
        original_thread_excepthook = threading.excepthook

        def custom_thread_excepthook(args):
            """Custom thread exception handler."""
            if not is_mongodb_background_error(args.exc_type, args.exc_value, args.exc_traceback):
                # Use default handler for non-MongoDB errors
                original_thread_excepthook(args)
            # Otherwise, silently suppress MongoDB background errors

        threading.excepthook = custom_thread_excepthook


def _truncate_error_message(error: Exception, max_length: int = 200) -> str:
    """Truncate long error messages to keep logs clean."""
    error_str = str(error)
    # Remove verbose topology descriptions from MongoDB errors
    if "Topology Description" in error_str:
        parts = error_str.split("Topology Description")
        if parts:
            error_str = parts[0].strip()
    # Remove verbose DNS resolution details
    if "DNS operation timed out" in error_str or "resolution lifetime expired" in error_str:
        # Extract just the main error before DNS details
        if ":" in error_str:
            error_str = error_str.split(":")[0] + ": DNS resolution timeout"

    # Truncate if still too long
    if len(error_str) > max_length:
        error_str = error_str[:max_length] + "..."

    return error_str


def init_sentry() -> None:
    """Initialize Sentry error tracking if DSN is configured."""
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            # Enable performance monitoring
            # 100% in debug, 10% in production
            traces_sample_rate=1.0 if settings.DEBUG else 0.1,
            # Enable profiling (only in production to reduce overhead)
            profiles_sample_rate=0.1 if not settings.DEBUG else 0.0,
            # Add data like request headers and IP for users
            send_default_pii=True,
            # Set environment
            environment="development" if settings.DEBUG else "production",
            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above as breadcrumbs
                    event_level=logging.ERROR  # Send errors and above as events
                ),
            ],
            # Release tracking (optional - can be set from CI/CD)
            # release="dbrevel@1.0.0",
        )
        logger.info("✓ Sentry error tracking initialized")
    else:
        logger.info("ℹ️  Sentry DSN not configured - error tracking disabled")


# Install stderr filter FIRST (before anything else that might use stderr)
_install_stderr_filter()

# Initialize Sentry as early as possible (before FastAPI app creation)
init_sentry()

# Suppress MongoDB background errors early (before any MongoDB connections)
_suppress_mongodb_background_errors()


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

    # Validate database URL formats
    if settings.POSTGRES_URL and not settings.POSTGRES_URL.startswith(("postgresql://", "postgres://")):
        raise RuntimeError(
            f"Invalid POSTGRES_URL format. Must start with 'postgresql://' or 'postgres://'. "
            f"Got: {settings.POSTGRES_URL[:50]}..."
        )

    if settings.MONGODB_URL and not settings.MONGODB_URL.startswith(("mongodb://", "mongodb+srv://")):
        raise RuntimeError(
            f"Invalid MONGODB_URL format. Must start with 'mongodb://' or 'mongodb+srv://'. "
            f"Got: {settings.MONGODB_URL[:50]}..."
        )

    # Check for insecure default values in production mode
    if not settings.DEBUG:
        insecure_settings = []

        # Check SECRET_KEY
        if "change-in-production" in settings.SECRET_KEY.lower():
            insecure_settings.append("SECRET_KEY contains default value")

        # Check ENCRYPTION_KEY
        if hasattr(settings, 'ENCRYPTION_KEY'):
            encryption_key = settings.ENCRYPTION_KEY
            if "your-encryption-key" in encryption_key.lower():
                insecure_settings.append(
                    "ENCRYPTION_KEY contains default value")

            # Validate encryption key strength
            if len(encryption_key) < 32:
                insecure_settings.append(
                    f"ENCRYPTION_KEY is too short ({len(encryption_key)} chars, minimum 32)")

            # Check for basic entropy (at least some variety in characters)
            if len(set(encryption_key)) < 10:
                insecure_settings.append(
                    "ENCRYPTION_KEY has low entropy (too few unique characters)")

        # Check if SECRET_KEY is too short
        if len(settings.SECRET_KEY) < 32:
            insecure_settings.append(
                f"SECRET_KEY is too short ({len(settings.SECRET_KEY)} chars, minimum 32)")

        if insecure_settings:
            raise RuntimeError(
                "Insecure configuration detected in production mode:\n" +
                "\n".join(f"  - {issue}" for issue in insecure_settings) +
                "\nPlease update your .env file with secure values."
            )

    logger.info("✓ Environment validation passed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager"""
    import os
    
    # Check if we're in test mode
    is_testing = os.getenv("TESTING", "false").lower() == "true"
    
    # Suppress MongoDB background reconnection errors at multiple levels
    # 1. Suppress log messages from pymongo background tasks (set to CRITICAL to be more aggressive)
    logging.getLogger("pymongo.synchronous.pool").setLevel(logging.CRITICAL)
    logging.getLogger("pymongo.synchronous.mongo_client").setLevel(
        logging.CRITICAL)
    logging.getLogger("pymongo.synchronous.topology").setLevel(
        logging.CRITICAL)
    logging.getLogger("pymongo.synchronous.server_selection").setLevel(
        logging.CRITICAL)
    # Suppress motor (async pymongo) background noise too
    logging.getLogger("motor").setLevel(logging.WARNING)

    # 2. Suppress exception tracebacks from background reconnection attempts
    # (Already installed early, but ensure it's active)
    _suppress_mongodb_background_errors()

    # Validate environment before starting
    validate_environment()

    # Skip database initialization in test mode
    if is_testing:
        logger.info("⚠️  Running in TESTING mode - skipping database initialization")
        yield
        return

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
                    "⚠️  WARNING: Demo project exists but NOT accessible via API key lookup!")
                print("   Demo queries will fail with 'Invalid API key' errors")
                print("   Checking MongoDB connection and indexes...")
                by_id = await project_store.get_by_id_async(DEMO_PROJECT_ID)
                if by_id:
                    print(f"   ✓ Project found by ID: {by_id.name}")
                    print(
                        "   ✗ But lookup by API key fails - check indexes or query logic")
                else:
                    print("   ✗ Project not found by ID either - was not created!")
    except Exception as e:
        error_msg = _truncate_error_message(e)
        logger.warning(
            "Could not verify demo project (MongoDB may be unreachable): %s. "
            "Demo queries will fail until MongoDB is available.", error_msg
        )

    # Ensure default admin user exists (non-blocking - don't fail startup)
    try:
        await ensure_admin_user()
    except Exception as e:
        error_msg = _truncate_error_message(e)
        logger.warning(
            "Could not ensure admin user (MongoDB may be unreachable): %s. "
            "Admin login will fail until MongoDB is available.", error_msg
        )

    yield

    # Shutdown - with timeout to prevent hanging
    logger.info("Starting graceful shutdown...")

    # Set a maximum shutdown time - if we exceed this, we'll force exit
    shutdown_start = asyncio.get_event_loop().time()
    max_shutdown_time = 3.0  # 3 seconds max for shutdown

    try:
        # Shutdown adapters with timeout
        await asyncio.wait_for(adapter_factory.shutdown(), timeout=2.0)
        logger.info("✓ Adapter factory shutdown complete")
    except asyncio.TimeoutError:
        logger.warning(
            "⚠️  Adapter factory shutdown timed out (continuing anyway)")
    except Exception as e:
        logger.error(
            f"Error during adapter factory shutdown: {e}", exc_info=True)

    # Close MongoDB clients from stores (they have background tasks)
    # Use a single timeout for all store closures
    try:
        async def close_all_stores():
            from app.core.account_store import get_account_store
            from app.core.project_store import get_project_store
            from app.core.user_store import user_store

            # Close all stores in parallel
            tasks = []

            if user_store and hasattr(user_store, 'client') and user_store.client:
                tasks.append(("user_store", user_store.client))

            project_store = get_project_store()
            if project_store and hasattr(project_store, 'client') and project_store.client:
                tasks.append(("project_store", project_store.client))

            account_store = get_account_store()
            if account_store and hasattr(account_store, 'client') and account_store.client:
                tasks.append(("account_store", account_store.client))

            # Close all clients
            for name, client in tasks:
                try:
                    client.close()
                    logger.debug(f"Closed {name} client")
                except Exception as e:
                    logger.warning(f"Error closing {name}: {e}")

        await asyncio.wait_for(close_all_stores(), timeout=1.0)
        logger.info("✓ All store clients closed")
    except asyncio.TimeoutError:
        logger.warning("⚠️  Store closure timed out (continuing anyway)")
    except Exception as e:
        logger.error(f"Error closing store connections: {e}", exc_info=True)

    # Check if we've exceeded max shutdown time
    shutdown_elapsed = asyncio.get_event_loop().time() - shutdown_start
    if shutdown_elapsed > max_shutdown_time:
        logger.warning(
            f"⚠️  Shutdown took {shutdown_elapsed:.2f}s (exceeded {max_shutdown_time}s limit)")

    logger.info("✓ Shutdown complete")

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

# Add rate limiting middleware (if limiter is initialized)
if limiter is not None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, safe_rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)
    logger.info("Rate limiting middleware enabled")
else:
    logger.warning("Rate limiting disabled (limiter not initialized)")

# Add Prometheus metrics middleware
app.add_middleware(PrometheusMiddleware)
logger.info("Prometheus metrics middleware enabled")

# Request logging middleware (before CORS)


@app.middleware("http")
async def log_requests(request, call_next):
    """Log request method, path, and response status/duration."""
    import time
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(
            "%s %s %s (%.3fs)",
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            "%s %s ERROR after %.3fs: %s",
            request.method,
            request.url.path,
            process_time,
            e,
            exc_info=True,
        )
        raise

# CORS Configuration
# Configured to allow requests from frontend and SDK clients
# Supports multiple origins (comma-separated in ALLOWED_ORIGINS env var)
# In production, headers are restricted for security
if settings.DEBUG:
    # Development: Allow all headers for easier testing
    allowed_headers = ["*"]
    exposed_headers = ["*"]
else:
    # Production: Restrict to specific headers needed by the application
    allowed_headers = [
        "Content-Type",
        "Authorization",
        "X-Project-Key",
        "Accept",
        "Origin",
        "X-Requested-With",
    ]
    exposed_headers = [
        "Content-Type",
        "X-Trace-Id",
        "X-Request-Id",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,  # Required for cookies/auth tokens
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=allowed_headers,
    expose_headers=exposed_headers,
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


@app.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    return get_metrics_response()


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
