"""Account configuration and resolution for multi-account SaaS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from app.core.config import settings
from fastapi import Header, HTTPException, status


@dataclass
class AccountConfig:
    """Per-account configuration for databases and Gemini usage."""

    id: str
    name: str
    api_key: str
    postgres_url: str
    mongodb_url: str
    gemini_mode: str  # "platform" or "byo"
    gemini_api_key: Optional[str] = None


# In-memory account registry (v1: hard-coded / env-based)
ACCOUNTS_BY_KEY: Dict[str, AccountConfig] = {}


def _load_default_account() -> None:
    """
    Initialize a default account from global settings.

    This keeps early SaaS and local development simple while
    still routing all requests through an account abstraction.
    """

    # In a real SaaS, this would come from an account store (DB/Config)
    default_api_key = "dbrevel_default_account_key"

    default_account = AccountConfig(
        id="default",
        name="Default Account",
        api_key=default_api_key,
        postgres_url=settings.POSTGRES_URL,
        mongodb_url=settings.MONGODB_URL,
        gemini_mode="platform",
        gemini_api_key=None,
    )

    ACCOUNTS_BY_KEY[default_api_key] = default_account


_load_default_account()


async def get_account_by_api_key_async(api_key: str) -> AccountConfig:
    """
    Lookup account configuration by API key.

    Only project API keys are supported. Each project has its own unique API key
    with separate database connections.
    """
    # Look up project by API key
    from app.core.project_store import get_project_store

    project_store = get_project_store()
    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    project = await project_store.get_by_api_key_async(api_key)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key. Please create a project in your dashboard to get an API key.",
        )

    # Get parent account for Gemini configuration
    from app.core.account_store import get_account_store

    account_store = get_account_store()
    parent_account = None
    if account_store:
        parent_account = await account_store.get_by_id_async(project.account_id)

    # Build AccountConfig from project data
    return AccountConfig(
        id=project.account_id,
        name=f"{parent_account.name if parent_account else 'Unknown'} - {project.name}",
        api_key=project.api_key,
        postgres_url=project.postgres_url,
        mongodb_url=project.mongodb_url,
        gemini_mode=parent_account.gemini_mode if parent_account else "platform",
        gemini_api_key=parent_account.gemini_api_key if parent_account else None,
    )


async def get_account_config(
    x_project_key: Optional[str] = Header(
        None,
        alias="X-Project-Key",
        description="Project API key. Leave empty to use demo project with sample data, or use `dbrevel_demo_project_key` explicitly. Get your own API key from the dashboard.",
        example="dbrevel_demo_project_key",
    ),
) -> Optional[AccountConfig]:
    """
    FastAPI dependency to resolve AccountConfig from request headers.

    Returns None if no API key provided (for endpoints that support both JWT and API key).
    For endpoints that require API key, use get_account_config_required().

    For SaaS usage, requests can include:
        X-Project-Key: <project_api_key>
    """
    if not x_project_key:
        return None

    return await get_account_by_api_key_async(x_project_key)


async def get_account_config_required(
    x_project_key: Optional[str] = Header(None, alias="X-Project-Key"),
) -> AccountConfig:
    """
    FastAPI dependency to resolve AccountConfig from request headers (required).

    Raises HTTPException if API key is missing.
    """
    if not x_project_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing project API key",
        )

    return await get_account_by_api_key_async(x_project_key)
