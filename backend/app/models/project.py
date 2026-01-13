"""
Project models for multi-project support.

Each tenant can have multiple projects with separate database configurations.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Project(BaseModel):
    """Project database model."""

    id: str = Field(..., description="Project ID in format 'prj_<uuid>'")
    name: str = Field(..., description="Project name (e.g., 'Production', 'Staging')")
    account_id: str = Field(..., description="Parent account ID")
    api_key: str = Field(..., description="Unique project API key for authentication")
    postgres_url: str = Field(default="", description="PostgreSQL connection URL (encrypted)")
    mongodb_url: str = Field(default="", description="MongoDB connection URL (encrypted)")
    created_at: datetime = Field(..., description="Project creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(default=True, description="Active status (soft delete)")


class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project."""

    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    postgres_url: Optional[str] = Field(default=None, description="PostgreSQL connection URL")
    mongodb_url: Optional[str] = Field(default=None, description="MongoDB connection URL")


class ProjectUpdateRequest(BaseModel):
    """Request model for updating a project."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100, description="Project name")
    postgres_url: Optional[str] = Field(default=None, description="PostgreSQL connection URL")
    mongodb_url: Optional[str] = Field(default=None, description="MongoDB connection URL")


class ProjectResponse(BaseModel):
    """Response model for project details (with sensitive data masked)."""

    id: str
    name: str
    account_id: str
    api_key: str  # Only shown on creation, masked on retrieval
    postgres_url: str  # Masked for security
    mongodb_url: str  # Masked for security
    created_at: datetime
    updated_at: datetime
    is_active: bool


class ProjectListResponse(BaseModel):
    """Response model for project list (without sensitive data)."""

    id: str
    name: str
    is_active: bool
    created_at: datetime


class ApiKeyRotateResponse(BaseModel):
    """Response model for API key rotation."""

    project_id: str
    new_api_key: str
    rotated_at: datetime


class DatabaseConnectionTestRequest(BaseModel):
    """Request model for testing database connections."""

    project_id: Optional[str] = Field(default=None, description="Project ID to test connections for (uses project's saved URLs)")
    postgres_url: Optional[str] = Field(default=None, description="PostgreSQL connection URL to test (if not using project_id)")
    mongodb_url: Optional[str] = Field(default=None, description="MongoDB connection URL to test (if not using project_id)")


class DatabaseConnectionTestResponse(BaseModel):
    """Response model for database connection test results."""

    postgres: Optional[dict] = Field(default=None, description="PostgreSQL test result")
    mongodb: Optional[dict] = Field(default=None, description="MongoDB test result")


class ApiKeyRevealResponse(BaseModel):
    """Response model for API key reveal."""

    project_id: str
    api_key: str
