"""
Project models for multi-project support.

Each tenant can have multiple projects with separate database configurations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Database configuration for a project."""
    type: str = Field(..., description="Database type (postgres, mongodb, mysql, redis, etc.)")
    connection_url: str = Field(..., description="Database connection URL (encrypted)")


class Project(BaseModel):
    """Project database model."""

    id: str = Field(..., description="Project ID in format 'prj_<uuid>'")
    name: str = Field(...,
                      description="Project name (e.g., 'Production', 'Staging')")
    account_id: str = Field(..., description="Parent account ID")
    api_key: str = Field(...,
                         description="Unique project API key for authentication")
    # Legacy fields (maintained for backward compatibility)
    postgres_url: str = Field(
        default="", description="PostgreSQL connection URL (encrypted) - legacy")
    mongodb_url: str = Field(
        default="", description="MongoDB connection URL (encrypted) - legacy")
    # New format: list of database configurations
    databases: List[DatabaseConfig] = Field(
        default_factory=list, description="List of database configurations (new format)")
    created_at: datetime = Field(..., description="Project creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_active: bool = Field(
        default=True, description="Active status (soft delete)")


class ProjectCreateRequest(BaseModel):
    """Request model for creating a new project."""

    name: str = Field(..., min_length=1, max_length=100,
                      description="Project name")
    # Legacy fields (maintained for backward compatibility)
    postgres_url: Optional[str] = Field(
        default=None, description="PostgreSQL connection URL (legacy)")
    mongodb_url: Optional[str] = Field(
        default=None, description="MongoDB connection URL (legacy)")
    # New format: list of database configurations
    databases: Optional[List[Dict[str, str]]] = Field(
        default=None, description="List of database configurations (new format: [{'type': 'postgres', 'connection_url': '...'}, ...])")


class ProjectUpdateRequest(BaseModel):
    """Request model for updating a project."""

    name: Optional[str] = Field(
        default=None, min_length=1, max_length=100, description="Project name")
    # Legacy fields (maintained for backward compatibility)
    postgres_url: Optional[str] = Field(
        default=None, description="PostgreSQL connection URL (legacy)")
    mongodb_url: Optional[str] = Field(
        default=None, description="MongoDB connection URL (legacy)")
    # New format: list of database configurations
    databases: Optional[List[Dict[str, str]]] = Field(
        default=None, description="List of database configurations (new format)")


class ProjectResponse(BaseModel):
    """Response model for project details (with sensitive data masked)."""

    id: str
    name: str
    account_id: str
    api_key: str  # Only shown on creation, masked on retrieval
    postgres_url: str  # Masked for security
    mongodb_url: str  # Masked for security
    databases: List[Dict[str, str]] = Field(
        default_factory=list, description="List of database configurations (masked)")
    created_at: datetime
    updated_at: datetime
    is_active: bool


class ProjectListResponse(BaseModel):
    """Response model for project list (without sensitive data)."""

    id: str
    name: str
    is_active: bool
    created_at: datetime


class ProjectApiKeyRotateResponse(BaseModel):
    """Response model for API key rotation."""

    project_id: str
    new_api_key: str
    rotated_at: datetime


class ProjectConnectionTestRequest(BaseModel):
    """Request model for testing database connections."""

    project_id: Optional[str] = Field(
        default=None, description="Project ID to test connections for (uses project's saved URLs)")
    postgres_url: Optional[str] = Field(
        default=None, description="PostgreSQL connection URL to test (if not using project_id)")
    mongodb_url: Optional[str] = Field(
        default=None, description="MongoDB connection URL to test (if not using project_id)")


class ProjectConnectionTestResponse(BaseModel):
    """Response model for database connection test results."""

    postgres: Optional[Dict[str, Any]] = Field(
        default=None, description="PostgreSQL test result")
    mongodb: Optional[Dict[str, Any]] = Field(
        default=None, description="MongoDB test result")


class ProjectApiKeyRevealResponse(BaseModel):
    """Response model for API key reveal."""

    project_id: str
    api_key: str
