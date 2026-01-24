"""Pydantic models for account management."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class Account(BaseModel):
    """Account database model."""

    id: str = Field(..., description="Account ID")
    name: str = Field(..., description="Account name")
    api_key: str = Field(..., description="Account API key")
    postgres_url: str = Field(..., description="PostgreSQL connection URL")
    mongodb_url: str = Field(..., description="MongoDB connection URL")
    gemini_mode: str = Field(default="platform", description="Gemini mode")
    gemini_api_key: Optional[str] = Field(None, description="Gemini API key")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(default=True, description="Active status")


class AccountCreateRequest(BaseModel):
    """Request model for creating a new account."""

    name: str = Field(..., description="Account name")
    postgres_url: str = Field(..., description="PostgreSQL connection URL")
    mongodb_url: str = Field(..., description="MongoDB connection URL")
    gemini_mode: str = Field(
        default="platform",
        description="Gemini mode: 'platform' or 'byo'",
    )
    gemini_api_key: Optional[str] = Field(
        None,
        description="Gemini API key (required if gemini_mode is 'byo')",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Acme Corp",
                "postgres_url": "postgresql://user:pass@localhost:5432/acme_db",
                "mongodb_url": "mongodb://localhost:27017/acme_db",
                "gemini_mode": "platform",
            }
        }
    }


class AccountUpdateRequest(BaseModel):
    """Request model for updating an account."""

    name: Optional[str] = None
    postgres_url: Optional[str] = None
    mongodb_url: Optional[str] = None
    gemini_mode: Optional[str] = None
    gemini_api_key: Optional[str] = None


class AccountResponse(BaseModel):
    """Response model for account information."""

    id: str
    name: str
    api_key: str  # Only returned on creation/rotation
    postgres_url: str  # Masked for security
    mongodb_url: str  # Masked for security
    gemini_mode: str
    gemini_api_key: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "account_1",
                "name": "Acme Corp",
                "api_key": "dbrevel_abc123...",
                "postgres_url": "postgresql://...",
                "mongodb_url": "mongodb://...",
                "gemini_mode": "platform",
            }
        }
    }


class AccountListResponse(BaseModel):
    """Response model for listing accounts (without sensitive data)."""

    id: str
    name: str
    gemini_mode: str
    # Note: api_key is NOT included in list responses for security

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "account_1",
                "name": "Acme Corp",
                "gemini_mode": "platform",
            }
        }
    }


class AccountApiKeyRotateResponse(BaseModel):
    """Response model for API key rotation."""

    account_id: str
    new_api_key: str
    rotated_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "account_id": "account_1",
                "new_api_key": "dbrevel_new_key_123...",
                "rotated_at": "2024-01-01T12:00:00Z",
            }
        }
    }


class AccountConnectionTestRequest(BaseModel):
    """Request model for testing database connections."""

    postgres_url: Optional[str] = Field(
        None, description="PostgreSQL connection URL to test"
    )
    mongodb_url: Optional[str] = Field(
        None, description="MongoDB connection URL to test"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "postgres_url": "postgresql://user:pass@localhost:5432/db",
                "mongodb_url": "mongodb://localhost:27017/db",
            }
        }
    }


class AccountConnectionTestResponse(BaseModel):
    """Response model for database connection test results."""

    postgres: Optional[Dict[str, Any]] = None
    mongodb: Optional[Dict[str, Any]] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "postgres": {
                    "success": True,
                    "schema_preview": {
                        "database_name": "mydb",
                        "table_count": 5,
                    },
                },
                "mongodb": {
                    "success": False,
                    "error": "Connection refused",
                },
            }
        }
    }


class DatabaseUpdateRequest(BaseModel):
    """Request model for updating database URLs."""

    postgres_url: Optional[str] = Field(
        None, description="New PostgreSQL connection URL"
    )
    mongodb_url: Optional[str] = Field(None, description="New MongoDB connection URL")


class AccountApiKeyRevealResponse(BaseModel):
    """Response model for API key reveal."""

    account_id: str
    api_key: str
