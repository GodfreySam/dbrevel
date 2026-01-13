"""Account management API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from app.core.account_store import get_account_store
from app.core.account_store import MongoDBAccountStore
from app.core.account_keys import generate_account_key
from app.core.encryption import mask_database_url
from app.models.account import (
    AccountCreateRequest,
    AccountUpdateRequest,
    AccountResponse,
    AccountListResponse,
    ApiKeyRotateResponse,
)
from app.core.accounts import AccountConfig, get_account_config, get_account_config_required
from app.core.auth import get_current_user, get_current_user_optional, get_current_admin
from app.core.db_test import test_postgres_connection, test_mongodb_connection
from app.models.account import (
    DatabaseConnectionTestRequest,
    DatabaseConnectionTestResponse,
    DatabaseUpdateRequest,
)
from app.models.user import User
from app.adapters.factory import adapter_factory

router = APIRouter(prefix="/accounts", tags=["accounts"])


async def get_account_by_id_async(account_id: str) -> Optional[AccountConfig]:
    """
    Helper function to get account by ID in an async context.

    Handles the async/sync mismatch by calling the async method directly
    when account_store is MongoDBAccountStore, avoiding event loop issues.
    """
    account_store = get_account_store()
    if account_store is None:
        return None
    if isinstance(account_store, MongoDBAccountStore):
        # Call async method directly since we're in an async context
        return await account_store._get_by_id_async(account_id)
    else:
        # Fall back to synchronous method for other store types
        return account_store.get_by_id(account_id)


async def list_accounts_async() -> List[AccountConfig]:
    """
    Helper function to list all accounts in an async context.

    Handles the async/sync mismatch by calling the async method directly
    when account_store is MongoDBAccountStore, avoiding event loop issues.
    """
    account_store = get_account_store()
    if account_store is None:
        return []
    if isinstance(account_store, MongoDBAccountStore):
        # Call async method directly since we're in an async context
        return await account_store._list_accounts_async()
    else:
        # Fall back to synchronous method for other store types
        return account_store.list_accounts()


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    request: AccountCreateRequest,
    admin: User = Depends(get_current_admin),
):
    """
    Create a new account.

    Generates a secure API key automatically.
    """
    # Generate API key
    api_key = generate_account_key()

    # Create account
    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )
    account = account_store.create_account(
        name=request.name,
        api_key=api_key,
        postgres_url=request.postgres_url,
        mongodb_url=request.mongodb_url,
        gemini_mode=request.gemini_mode,
        gemini_api_key=request.gemini_api_key,
    )

    # Mask database URLs for security
    return AccountResponse(
        id=account.id,
        name=account.name,
        api_key=account.api_key,  # Return key only on creation
        postgres_url=mask_database_url(account.postgres_url),
        mongodb_url=mask_database_url(account.mongodb_url),
        gemini_mode=account.gemini_mode,
        gemini_api_key=account.gemini_api_key,
    )


@router.get("", response_model=List[AccountListResponse])
async def list_accounts(admin: User = Depends(get_current_admin)):
    """
    List all accounts (without sensitive information like API keys).
    """
    accounts = await list_accounts_async()
    return [
        AccountListResponse(
            id=account.id,
            name=account.name,
            gemini_mode=account.gemini_mode,
        )
        for account in accounts
    ]


@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: str,
    admin: User = Depends(get_current_admin),
):
    """
    Get account details by ID.
    """
    account = await get_account_by_id_async(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    # Mask database URLs for security
    return AccountResponse(
        id=account.id,
        name=account.name,
        api_key=account.api_key,  # Include key for admin viewing
        postgres_url=mask_database_url(account.postgres_url),
        mongodb_url=mask_database_url(account.mongodb_url),
        gemini_mode=account.gemini_mode,
        gemini_api_key=account.gemini_api_key,
    )


@router.patch("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    request: AccountUpdateRequest,
    admin: User = Depends(get_current_admin),
):
    """
    Update account configuration.
    """
    account = await get_account_by_id_async(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    updates = request.model_dump(exclude_unset=True)
    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )
    updated_account = account_store.update_account(account_id, **updates)

    if not updated_account:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update account",
        )

    # Mask database URLs for security
    return AccountResponse(
        id=updated_account.id,
        name=updated_account.name,
        api_key=updated_account.api_key,
        postgres_url=mask_database_url(updated_account.postgres_url),
        mongodb_url=mask_database_url(updated_account.mongodb_url),
        gemini_mode=updated_account.gemini_mode,
        gemini_api_key=updated_account.gemini_api_key,
    )


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    admin: User = Depends(get_current_admin),
):
    """
    Delete an account.

    Warning: This permanently deletes the account and invalidates their API key.
    """
    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )
    success = account_store.delete_account(account_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    return None


@router.post("/{account_id}/rotate-key", response_model=ApiKeyRotateResponse)
async def rotate_api_key(
    account_id: str,
    admin: User = Depends(get_current_admin),
):
    """
    Rotate an account's API key.

    Generates a new API key and invalidates the old one.
    The old key will immediately stop working.
    """
    account = await get_account_by_id_async(account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account {account_id} not found",
        )

    # Generate new key
    new_api_key = generate_account_key()

    # Rotate key
    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )
    old_key_hash = account_store.rotate_api_key(account_id, new_api_key)

    if not old_key_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate API key",
        )

    return ApiKeyRotateResponse(
        account_id=account_id,
        new_api_key=new_api_key,
        message="API key rotated successfully. Old key is now invalid.",
    )


@router.get("/me/info", response_model=AccountListResponse)
async def get_current_account_info(
    account: AccountConfig = Depends(get_account_config_required),
):
    """
    Get information about the current account (using their API key).

    This endpoint allows accounts to view their own information.
    Supports both API key (X-Project-Key header) and JWT token authentication.
    """
    return AccountListResponse(
        id=account.id,
        name=account.name,
        gemini_mode=account.gemini_mode,
    )


@router.get("/me/info-jwt", response_model=AccountResponse)
async def get_current_account_info_jwt(
    current_user: User = Depends(get_current_user),
):
    """
    Get full account information using JWT authentication.

    This endpoint is for frontend users who are logged in.
    Returns full account details including API key.
    """
    import logging

    # Log for debugging
    logging.info(f"Fetching account info for user {current_user.id} with account_id={current_user.account_id}")

    if not current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User does not have an account_id assigned",
        )

    # Use async helper to avoid event loop issues
    account = await get_account_by_id_async(current_user.account_id)

    if not account:
        # List all available accounts for debugging (in development only)
        try:
            all_accounts = await list_accounts_async()
            available_ids = [t.id for t in all_accounts] if all_accounts else []
        except Exception as e:
            logging.warning(f"Could not list accounts for debugging: {e}")
            available_ids = []
        logging.error(
            f"get_current_account_info_jwt: Account not found for account_id={current_user.account_id} "
            f"(user_id={current_user.id}, email={current_user.email}). "
            f"Available account IDs in database: {available_ids}. "
            f"This indicates a data consistency issue - user has account_id but account doesn't exist."
        )
        error_detail = (
            f"Account with id '{current_user.account_id}' not found. "
            f"User ID: {current_user.id}, Email: {current_user.email}. "
            f"This may indicate a data consistency issue. Please contact support."
        )
        if available_ids:
            error_detail += f" Available account IDs in database: {available_ids}"
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail,
        )

    # Mask database URLs for security (don't expose full connection strings)
    return AccountResponse(
        id=account.id,
        name=account.name,
        api_key=account.api_key,
        postgres_url=mask_database_url(account.postgres_url),
        mongodb_url=mask_database_url(account.mongodb_url),
        gemini_mode=account.gemini_mode,
        gemini_api_key=account.gemini_api_key,
    )


@router.post("/me/test-connection", response_model=DatabaseConnectionTestResponse)
async def test_database_connection(
    request: DatabaseConnectionTestRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    account: Optional[AccountConfig] = Depends(get_account_config),
):
    """
    Test database connections before saving.

    Tests PostgreSQL and/or MongoDB connections and returns connection status
    and schema preview. Does not save the URLs - use PATCH /me/databases to save.

    Supports both JWT (frontend) and API key (SDK) authentication.
    """
    # Determine account from either JWT user or API key
    account_config = None
    if current_user:
        # JWT auth - get account from user
        account_config = await get_account_by_id_async(current_user.account_id)
    elif account:
        # API key auth - account already resolved
        account_config = account

    if not account_config:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    results = DatabaseConnectionTestResponse()

    # Test PostgreSQL if provided
    if request.postgres_url:
        pg_result = await test_postgres_connection(request.postgres_url)
        results.postgres = pg_result.to_dict()

    # Test MongoDB if provided
    if request.mongodb_url:
        mongo_result = await test_mongodb_connection(request.mongodb_url)
        results.mongodb = mongo_result.to_dict()

    if not request.postgres_url and not request.mongodb_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one database URL (postgres_url or mongodb_url) is required",
        )

    return results


@router.patch("/me/databases", response_model=AccountResponse)
async def update_my_databases(
    request: DatabaseUpdateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    account: Optional[AccountConfig] = Depends(get_account_config),
):
    """
    Update your own database connection URLs.

    This will invalidate existing database adapters and re-initialize them
    with the new URLs on the next query.

    Supports both JWT (frontend) and API key (SDK) authentication.
    """
    # Determine account from either JWT user or API key
    account_config = None
    account_id = None

    if current_user:
        # JWT auth - get account from user
        account_id = current_user.account_id
        account_config = await get_account_by_id_async(account_id)
    elif account:
        # API key auth - account already resolved
        account_config = account
        account_id = account.id

    if not account_config or not account_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one database URL must be provided",
        )

    # Update account
    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )
    updated_account = account_store.update_account(account_id, **updates)

    if not updated_account:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update database URLs",
        )

    # Invalidate adapters for this account so they get re-initialized with new URLs
    # This is handled by adapter_factory on next query

    # Mask database URLs for security
    return AccountResponse(
        id=updated_account.id,
        name=updated_account.name,
        api_key=updated_account.api_key,
        postgres_url=mask_database_url(updated_account.postgres_url),
        mongodb_url=mask_database_url(updated_account.mongodb_url),
        gemini_mode=updated_account.gemini_mode,
        gemini_api_key=updated_account.gemini_api_key,
    )
