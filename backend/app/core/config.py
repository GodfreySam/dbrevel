"""Application configuration"""

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_HOST: str = "0.0.0.0"  # Override in .env
    API_PORT: int = 8000  # Override in .env
    DEBUG: bool = False  # Override in .env
    # CORS: Comma-separated list of allowed origins
    # Examples: "http://localhost:5173,https://app.dbrevel.com"
    # For development: Common Vite ports (5173 default, 3000 if configured)
    # For production: "https://app.dbrevel.com,https://admin.dbrevel.com"
    # Note: Vite dev server defaults to port 5173, but can be configured to 3000
    # Override in .env for production deployments
    ALLOWED_ORIGINS: str = (
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"  # Override in .env
    )

    # Gemini API
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"

    # Database URLs
    POSTGRES_URL: str
    MONGODB_URL: str
    REDIS_URL: str = ""

    # Connection Pool Settings (optional - defaults provided)
    POSTGRES_POOL_MIN_SIZE: int = 1
    POSTGRES_POOL_MAX_SIZE: int = 10
    MONGODB_POOL_MIN_SIZE: int = 1
    MONGODB_POOL_MAX_SIZE: int = 10

    # Demo Database URLs (cloud-hosted for consistency across all environments)
    # If set, these URLs will be used for demo account instead of deriving from POSTGRES_URL/MONGODB_URL
    # Optional: Direct PostgreSQL URL for demo (cloud-hosted PostgreSQL)
    DEMO_POSTGRES_URL: str = ""
    # Optional: Direct MongoDB URL for demo (e.g., Atlas)
    DEMO_MONGODB_URL: str = ""
    # Enable/disable automatic demo account creation on startup
    DEMO_ACCOUNT_ENABLED: bool = True

    # Encryption (for database connection strings)
    ENCRYPTION_KEY: str  # Override in .env

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"  # Override in .env
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Email (Zoho Mail)
    EMAIL_ENABLED: bool = True
    EMAIL_FROM_ADDRESS: str = "noreply@dbrevel.io"
    EMAIL_FROM_NAME: str = "DBRevel"
    SUPPORT_EMAIL: str = "support@dbrevel.io"
    ZOHO_SMTP_HOST: str = "smtp.zoho.com"
    ZOHO_SMTP_PORT: int = 587
    ZOHO_SMTP_USER: str = ""  # Your Zoho email address
    ZOHO_SMTP_PASSWORD: str = ""  # Your Zoho app-specific password
    EMAIL_USE_TLS: bool = True

    # Logging
    LOG_LEVEL: str = "INFO"

    # Sentry Error Tracking (optional - leave empty to disable)
    SENTRY_DSN: str = ""  # Override in .env

    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse allowed origins into list"""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",  # Ignore extra environment variables not defined in Settings
    }


settings = Settings()  # type: ignore[call-arg]
