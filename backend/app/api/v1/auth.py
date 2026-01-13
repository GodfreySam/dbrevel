"""Authentication API endpoints."""

import logging
from typing import Optional

from bson import ObjectId
import app.core.email_verification as email_verification_module
import app.core.password_reset as password_reset_module
import app.core.user_store as user_store_module
from app.core.auth import (create_access_token, get_current_user,
                           hash_password, verify_password)
from app.core.config import settings
from app.core.email_service import get_email_service
from app.core.account_keys import generate_account_key
from app.core.account_store import get_account_store
from app.models.user import (EmailVerificationRequest,
                             EmailVerificationResponse, PasswordChange,
                             PasswordReset, PasswordResetRequest,
                             PasswordResetResponse, TokenResponse, User,
                             UserCreate, UserLogin, UserResponse)
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter()


def _ensure_user_store():
    """Ensure user store is initialized (fallback if not initialized at startup)."""
    if user_store_module.user_store is None:
        # Extract base MongoDB URL (without database name) for user store
        # MONGODB_URL format: mongodb://host:port/database_name
        # We need: mongodb://host:port (base URL) for user store
        if '/' in settings.MONGODB_URL:
            # Split on last '/' to get base URL
            mongo_base_url = '/'.join(settings.MONGODB_URL.rsplit('/', 1)[:-1])
        else:
            mongo_base_url = settings.MONGODB_URL
        from app.core.user_store import init_user_store
        init_user_store(mongo_base_url, "dbrevel_platform")


def _ensure_email_verification_store():
    """Ensure email verification store is initialized (fallback if not initialized at startup)."""
    if email_verification_module.email_verification_store is None:
        # Extract base MongoDB URL (without database name) for email verification store
        if '/' in settings.MONGODB_URL:
            # Split on last '/' to get base URL
            mongo_base_url = '/'.join(settings.MONGODB_URL.rsplit('/', 1)[:-1])
        else:
            mongo_base_url = settings.MONGODB_URL
        from app.core.email_verification import init_email_verification_store
        init_email_verification_store(mongo_base_url, "dbrevel_platform")


def _ensure_password_reset_store():
    """Ensure password reset store is initialized (fallback if not initialized at startup)."""
    if password_reset_module.password_reset_store is None:
        # Extract base MongoDB URL (without database name) for password reset store
        if '/' in settings.MONGODB_URL:
            mongo_base_url = '/'.join(settings.MONGODB_URL.rsplit('/', 1)[:-1])
        else:
            mongo_base_url = settings.MONGODB_URL
        from app.core.password_reset import init_password_reset_store
        init_password_reset_store(mongo_base_url, "dbrevel_platform")


@router.post("/register", response_model=EmailVerificationResponse, status_code=status.HTTP_201_CREATED)
async def register(request: UserCreate):
    """
    Register a new user and create their account.

    Creates an account (billing entity) and a user. Also creates a default project
    with an API key for database access. Note: Accounts don't have API keys, only projects do.
    Sends an email verification OTP. User must verify email before accessing protected endpoints.
    """
    _ensure_user_store()

    # Access user_store through module to get the latest initialized value
    user_store = user_store_module.user_store
    if user_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized. Please restart the server.",
        )

    # Check if user already exists
    existing_user = await user_store.get_by_email(request.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    # Create account without API key (projects will have the API keys)
    # Use async method directly if account_store is MongoDBAccountStore (avoid event loop issues)
    from app.core.account_store import MongoDBAccountStore

    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )

    account = None
    account_id_for_cleanup = None

    try:
        if isinstance(account_store, MongoDBAccountStore):
            # Call async method directly since we're in an async context
            # This method already includes verification and will raise if account can't be persisted
            account = await account_store._create_account_async(
                name=request.name,
                api_key="",  # No account-level API key - projects have keys
                postgres_url="",  # Projects have their own DB URLs
                mongodb_url="",
                gemini_mode="platform",
                gemini_api_key=None,
            )
        else:
            # Fall back to synchronous method for other store types
            account = account_store.create_account(
                name=request.name,
                api_key="",  # No account-level API key - projects have keys
                postgres_url="",  # Projects have their own DB URLs
                mongodb_url="",
                gemini_mode="platform",
                gemini_api_key=None,
            )

        # Verify account was created successfully
        if not account or not account.id:
            logging.error(f"Registration: Failed to create account for user {request.email}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create account",
            )

        account_id_for_cleanup = account.id
        logging.info(f"Registration: Created account_id={account.id} for user {request.email}")

        # The _create_account_async method already verifies persistence internally
        # But we'll do one more verification here for extra safety
        import asyncio
        verify_account = None
        max_retries = 3
        retry_delay = 0.3  # seconds

        for attempt in range(max_retries):
            if isinstance(account_store, MongoDBAccountStore):
                verify_account = await account_store._get_by_id_async(account.id)
            else:
                verify_account = account_store.get_by_id(account.id)

            if verify_account:
                logging.info(f"Registration: Verified account_id={account.id} exists in database (attempt {attempt + 1})")
                break

            if attempt < max_retries - 1:
                logging.warning(
                    f"Registration: Account {account.id} not found on attempt {attempt + 1}, retrying in {retry_delay}s..."
                )
                await asyncio.sleep(retry_delay)
                retry_delay *= 1.5  # Gradual backoff

        if not verify_account:
            # Log all available accounts for debugging
            if isinstance(account_store, MongoDBAccountStore):
                try:
                    all_accounts = await account_store._list_accounts_async()
                    available_ids = [t.id for t in all_accounts] if all_accounts else []
                    logging.error(
                        f"Registration: Account {account.id} was created but cannot be retrieved after {max_retries} attempts. "
                        f"Available account IDs in database: {available_ids}"
                    )
                except Exception as e:
                    logging.error(f"Registration: Could not list accounts for debugging: {e}")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Account {account.id} was created but cannot be retrieved after multiple attempts. "
                       f"This indicates a persistence issue. Please contact support.",
            )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # If account creation failed, clean up any partially created account
        if account_id_for_cleanup:
            logging.error(
                f"Registration: Account creation failed for user {request.email}, "
                f"attempting to clean up account {account_id_for_cleanup}: {e}"
            )
            try:
                if isinstance(account_store, MongoDBAccountStore):
                    await account_store._delete_account_async(account_id_for_cleanup)
                else:
                    account_store.delete_account(account_id_for_cleanup)
                logging.info(f"Registration: Cleaned up account {account_id_for_cleanup}")
            except Exception as cleanup_error:
                logging.error(f"Registration: Failed to clean up account {account_id_for_cleanup}: {cleanup_error}")

        logging.error(f"Registration: Failed to create account for user {request.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create account: {str(e)}",
        )

    # Create user account
    try:
        user = await user_store.create_user(
            email=request.email,
            password=request.password,
            account_id=account.id,
        )
        logging.info(f"Registration: Created user {user.email} with account_id={user.account_id}")
    except Exception as e:
        # If user creation fails, clean up account
        logging.error(f"Registration: User creation failed for {request.email}, cleaning up account {account.id}: {e}")
        if isinstance(account_store, MongoDBAccountStore):
            await account_store._delete_account_async(account.id)
        else:
            account_store.delete_account(account.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )

    # Create default project for the user with API key
    from app.core.project_store import get_project_store, generate_project_id

    project_store = get_project_store()
    if project_store:
        try:
            project_api_key = generate_account_key()

            # Use demo database URLs as defaults if user doesn't provide their own
            default_postgres_url = request.postgres_url or settings.DEMO_POSTGRES_URL
            default_mongodb_url = request.mongodb_url or settings.DEMO_MONGODB_URL

            default_project = await project_store.create_project_async(
                name="My First Project",
                account_id=account.id,
                api_key=project_api_key,
                postgres_url=default_postgres_url,
                mongodb_url=default_mongodb_url,
                project_id=generate_project_id(),
            )
            # Log the project creation for debugging
            logging.info(f"Created default project for user {user.email}: {default_project.id}")
        except Exception as e:
            logging.error(f"Failed to create default project for user {user.email}: {e}")
            # Don't fail registration if project creation fails
            # User can create projects later via dashboard

    # Send email verification OTP
    _ensure_email_verification_store()
    email_verification_store = email_verification_module.email_verification_store
    if email_verification_store:
        try:
            otp = await email_verification_store.create_verification_otp(
                user.id, user.email, expires_in_minutes=30
            )
            email_service = get_email_service()
            await email_service.send_verification_email(user.email, otp)
        except Exception as e:
            logging.error(f"Failed to send verification email: {e}")
            # Don't fail registration if email sending fails, but log it
            return EmailVerificationResponse(
                message="Account created successfully, but verification email could not be sent. Please contact support or try resending verification."
            )

    return EmailVerificationResponse(
        message="Registration successful. Please check your email for the verification code."
    )


@router.post("/login", response_model=TokenResponse)
async def login(request: UserLogin):
    """
    Login with email and password.

    Returns a JWT token for authentication.
    """
    _ensure_user_store()

    # Access user_store through module to get the latest initialized value
    user_store = user_store_module.user_store
    if user_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized. Please restart the server.",
        )

    # Verify credentials
    user = await user_store.verify_user(request.email, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logging.info(f"Login: User {user.email} authenticated, user_id={user.id}, account_id={user.account_id}")

    # Check if email is verified
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your email and verify your account before logging in.",
        )

    # Get account info - use async method for MongoDB
    from app.core.account_store import MongoDBAccountStore

    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )

    logging.info(f"Login: Looking up account_id={user.account_id} for user {user.email}")

    if not user.account_id:
        logging.error(f"Login: User {user.email} has no account_id assigned!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User account is missing account assignment. Please contact support.",
        )

    if isinstance(account_store, MongoDBAccountStore):
        account = await account_store._get_by_id_async(user.account_id)
    else:
        account = account_store.get_by_id(user.account_id)

    if not account:
        # Log available account IDs for debugging
        available_ids = []
        if isinstance(account_store, MongoDBAccountStore):
            try:
                all_accounts = await account_store._list_accounts_async()
                available_ids = [t.id for t in all_accounts] if all_accounts else []
                logging.error(
                    f"Login: Account not found for user {user.email} (user_id={user.id}, account_id={user.account_id}). "
                    f"Available account IDs in database: {available_ids}"
                )
            except Exception as e:
                logging.error(f"Login: Could not list accounts for debugging: {e}")

        error_detail = (
            f"Account not found for user account. "
            f"User ID: {user.id}, Email: {user.email}, Account ID: {user.account_id}. "
            f"This indicates a data consistency issue. Please contact support."
        )
        if available_ids:
            error_detail += f" Available account IDs in database: {available_ids}"

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail,
        )

    # Generate JWT token with user role
    access_token = create_access_token(user.id, user.email, user.role)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            account_id=user.account_id,
            account_name=account.name,
            created_at=user.created_at,
            last_login=user.last_login,
            role=user.role,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user information.

    Requires valid JWT token in Authorization header.
    """
    # Get account info
    from app.core.account_store import MongoDBAccountStore

    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )

    logging.info(
        f"get_current_user_info: Fetching account for user {current_user.email} "
        f"(user_id={current_user.id}, account_id={current_user.account_id})"
    )

    if not current_user.account_id:
        logging.error(
            f"get_current_user_info: User {current_user.email} (id={current_user.id}) has no account_id assigned"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User account is missing account assignment. User ID: {current_user.id}, Email: {current_user.email}. Please contact support.",
        )

    if isinstance(account_store, MongoDBAccountStore):
        account = await account_store._get_by_id_async(current_user.account_id)
    else:
        account = account_store.get_by_id(current_user.account_id)

    if not account:
        # Log available account IDs for debugging
        available_ids = []
        if isinstance(account_store, MongoDBAccountStore):
            try:
                all_accounts = await account_store._list_accounts_async()
                available_ids = [t.id for t in all_accounts] if all_accounts else []
                logging.error(
                    f"get_current_user_info: Account not found for user {current_user.email} "
                    f"(user_id={current_user.id}, account_id={current_user.account_id}). "
                    f"Available account IDs in database: {available_ids}"
                )
            except Exception as e:
                logging.error(f"get_current_user_info: Could not list accounts for debugging: {e}")

        error_detail = (
            f"Account not found for user account. "
            f"User ID: {current_user.id}, Email: {current_user.email}, Account ID: {current_user.account_id}. "
            f"This indicates a data consistency issue. Please contact support."
        )
        if available_ids:
            error_detail += f" Available account IDs in database: {available_ids}"

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail,
        )

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        account_id=current_user.account_id,
        account_name=account.name,
        created_at=current_user.created_at,
        last_login=current_user.last_login,
        email_verified=current_user.email_verified,
    )


@router.post("/verify-email", response_model=TokenResponse)
async def verify_email(request: EmailVerificationRequest):
    """
    Verify user email address with OTP code.

    After registration, users receive an OTP code via email.
    This endpoint verifies the code and marks the email as verified.
    """
    _ensure_user_store()
    _ensure_email_verification_store()

    # Access stores through modules to get the latest initialized values
    user_store = user_store_module.user_store
    email_verification_store = email_verification_module.email_verification_store

    if user_store is None or email_verification_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stores not initialized. Please restart the server.",
        )

    # Get user first
    user = await user_store.get_by_email(request.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    # Check if already verified - return token and user data if so
    if user.email_verified:
        # Get account info
        from app.core.account_store import MongoDBAccountStore

        account_store = get_account_store()
        if account_store is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Account store not initialized. Please restart the server.",
            )
        if isinstance(account_store, MongoDBAccountStore):
            account = await account_store._get_by_id_async(user.account_id)
        else:
            account = account_store.get_by_id(user.account_id)

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            )

        # Generate JWT token and return
        access_token = create_access_token(user.id, user.email, user.role)
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=UserResponse(
                id=user.id,
                email=user.email,
                account_id=user.account_id,
                account_name=account.name,
                created_at=user.created_at,
                last_login=user.last_login,
                email_verified=True,
                role=user.role,
            ),
        )

    # OTP is already validated and stripped by Pydantic validator
    # Verify OTP
    otp_doc = await email_verification_store.verify_otp(request.email, request.otp)
    if not otp_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    # Verify user_id matches
    if otp_doc["user_id"] != user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OTP does not match user",
        )

    # Mark email as verified
    logging.info(f"verify_email: Marking email as verified for user {user.email} (user_id={user.id})")
    verification_success = await user_store.mark_email_verified(user.id)
    if not verification_success:
        logging.error(
            f"verify_email: Failed to mark email as verified for user {user.email} (user_id={user.id}). "
            f"Update may have failed or user may not exist."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email verification status. Please try again.",
        )

    # Mark OTP as used
    await email_verification_store.mark_otp_used(request.email, request.otp)

    # Invalidate all other verification OTPs for this user
    await email_verification_store.invalidate_user_otps(user.id)

    # Refresh user object to get updated email_verified status
    # Retry a few times to ensure database update is visible (MongoDB write concern)
    import asyncio
    user_id_for_refresh = user.id
    user_email_for_logging = user.email
    refreshed_user = None
    max_retries = 3
    for attempt in range(max_retries):
        logging.info(f"verify_email: Refreshing user object for {user_email_for_logging} (user_id={user_id_for_refresh}) - attempt {attempt + 1}")
        refreshed_user = await user_store.get_by_id(user_id_for_refresh)
        if refreshed_user and refreshed_user.email_verified:
            logging.info(
                f"verify_email: User {refreshed_user.email} (id={refreshed_user.id}) email verification confirmed: {refreshed_user.email_verified}"
            )
            break
        if attempt < max_retries - 1:
            await asyncio.sleep(0.2)  # Small delay to allow MongoDB write to propagate

    if not refreshed_user:
        logging.error(f"verify_email: User {request.email} (id={user_id_for_refresh}) not found after verification!")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found after verification",
        )

    if not refreshed_user.email_verified:
        logging.error(
            f"verify_email: CRITICAL - User {refreshed_user.email} (id={refreshed_user.id}) email_verified is still False "
            f"after {max_retries} refresh attempts. Database update may have failed."
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification status was not updated. Please try verifying again or contact support.",
        )

    # Use refreshed user for the rest of the endpoint
    user = refreshed_user
    logging.info(
        f"verify_email: User {user.email} (id={user.id}) email verification status confirmed: {user.email_verified}"
    )

    # Get account info
    from app.core.account_store import MongoDBAccountStore

    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )

    logging.info(
        f"verify_email: Looking up account for user {user.email} (user_id={user.id}, account_id={user.account_id})"
    )

    if isinstance(account_store, MongoDBAccountStore):
        account = await account_store._get_by_id_async(user.account_id)
    else:
        account = account_store.get_by_id(user.account_id)

    if not account:
        available_ids = []
        if isinstance(account_store, MongoDBAccountStore):
            try:
                all_accounts = await account_store._list_accounts_async()
                available_ids = [t.id for t in all_accounts] if all_accounts else []
                logging.error(
                    f"verify_email: Account not found for user {user.email} (user_id={user.id}, account_id={user.account_id}). "
                    f"Available account IDs: {available_ids}"
                )
            except Exception as e:
                logging.error(f"verify_email: Could not list accounts: {e}")

        error_detail = (
            f"Account not found for user account. "
            f"User ID: {user.id}, Email: {user.email}, Account ID: {user.account_id}. "
            f"Please contact support."
        )
        if available_ids:
            error_detail += f" Available account IDs: {available_ids}"

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=error_detail,
        )

    logging.info(f"verify_email: Account found for user {user.email}. Generating JWT token.")

    # Generate JWT token with user role
    access_token = create_access_token(user.id, user.email, user.role)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            account_id=user.account_id,
            account_name=account.name,
            created_at=user.created_at,
            last_login=user.last_login,
            email_verified=user.email_verified,
            role=user.role,
        ),
    )


@router.post("/resend-verification", response_model=dict)
async def resend_verification_email(email: str):
    """
    Resend email verification OTP.

    Sends a new verification email to the user if their email is not yet verified.
    """
    _ensure_user_store()
    _ensure_email_verification_store()

    # Access stores through modules to get the latest initialized values
    user_store = user_store_module.user_store
    email_verification_store = email_verification_module.email_verification_store

    if user_store is None or email_verification_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stores not initialized. Please restart the server.",
        )

    # Get user
    user = await user_store.get_by_email(email)
    if not user:
        # Don't reveal if user exists or not (security best practice)
        return {
            "message": "If an account with that email exists and is unverified, a verification email has been sent."
        }

    # Check if already verified
    if user.email_verified:
        return {
            "message": "Email already verified",
            "verified": True
        }

    # Generate and send new OTP
    try:
        otp = await email_verification_store.create_verification_otp(
            user.id, user.email, expires_in_minutes=30
        )
        email_service = get_email_service()
        await email_service.send_verification_email(user.email, otp)
        return {
            "message": "Verification email sent. Please check your inbox."
        }
    except Exception as e:
        logging.error(f"Failed to send verification email: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Please try again later.",
        )


@router.post("/forgot-password", response_model=PasswordResetResponse)
async def forgot_password(request: PasswordResetRequest):
    """
    Request a password reset OTP.

    Sends a 6-digit OTP code to the user's email (if account exists).
    OTP expires in 10 minutes.
    For security, always returns success message even if email doesn't exist.
    """
    _ensure_user_store()
    _ensure_password_reset_store()

    # Access stores through modules to get the latest initialized values
    user_store = user_store_module.user_store
    password_reset_store = password_reset_module.password_reset_store

    if user_store is None or password_reset_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stores not initialized. Please restart the server.",
        )

    # Check if user exists
    user = await user_store.get_by_email(request.email)
    if user:
        # Generate OTP
        otp_code = await password_reset_store.create_reset_otp(
            user.id,
            user.email,
            expires_in_minutes=10
        )

        # Send OTP email
        email_service = get_email_service()
        await email_service.send_otp_email(user.email, otp_code)

    # Always return success message (security best practice - don't reveal if email exists)
    return PasswordResetResponse()


@router.post("/reset-password", response_model=TokenResponse)
async def reset_password(request: PasswordReset):
    """
    Reset password using an OTP code.

    Validates the OTP and updates the user's password.
    Returns a new JWT token for immediate login.
    """
    _ensure_user_store()
    _ensure_password_reset_store()

    # Access stores through modules to get the latest initialized values
    user_store = user_store_module.user_store
    password_reset_store = password_reset_module.password_reset_store

    if user_store is None or password_reset_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stores not initialized. Please restart the server.",
        )

    # Verify OTP
    otp_doc = await password_reset_store.verify_otp(request.email, request.otp)
    if not otp_doc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OTP code. Please request a new one.",
        )

    # Get user
    user = await user_store.get_by_id(otp_doc["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Verify email matches
    if user.email != request.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email does not match OTP",
        )

    # Update password
    new_password_hash = hash_password(request.new_password)
    if not user_store.db:
        await user_store._ensure_connected()
    await user_store.db.users.update_one(
        {"_id": ObjectId(user.id)},
        {"$set": {"password_hash": new_password_hash}}
    )

    # Mark OTP as used
    await password_reset_store.mark_otp_used(request.email, request.otp)

    # Invalidate all other reset OTPs for this user
    await password_reset_store.invalidate_user_otps(user.id)

    # Get account info - use async method for MongoDB
    from app.core.account_store import MongoDBAccountStore

    account_store = get_account_store()
    if account_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized. Please restart the server.",
        )
    if isinstance(account_store, MongoDBAccountStore):
        account = await account_store._get_by_id_async(user.account_id)
    else:
        account = account_store.get_by_id(user.account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    # Generate new JWT token with user role
    access_token = create_access_token(user.id, user.email, user.role)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            account_id=user.account_id,
            account_name=account.name,
            created_at=user.created_at,
            last_login=user.last_login,
            role=user.role,
        ),
    )


@router.post("/change-password", response_model=dict)
async def change_password(
    request: PasswordChange,
    current_user: User = Depends(get_current_user),
):
    """
    Change password for authenticated user.

    Requires current password verification.
    """
    _ensure_user_store()
    _ensure_password_reset_store()

    # Access stores through modules to get the latest initialized values
    user_store = user_store_module.user_store
    password_reset_store = password_reset_module.password_reset_store

    if user_store is None or password_reset_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stores not initialized. Please restart the server.",
        )

    # Verify current password
    if not verify_password(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    new_password_hash = hash_password(request.new_password)
    if user_store.db is None:
        await user_store._ensure_connected()
    await user_store.db.users.update_one(
        {"_id": ObjectId(current_user.id)},
        {"$set": {"password_hash": new_password_hash}}
    )

    # Invalidate all reset OTPs for this user (security best practice)
    await password_reset_store.invalidate_user_otps(current_user.id)

    return {"message": "Password changed successfully"}


@router.get("/debug", response_model=dict)
async def debug_user_state(
    email: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
):
    """
    Diagnostic endpoint to check user state (development only).

    Returns user email_verified status, account_id, and whether account exists.
    This endpoint is for debugging authentication issues.
    """
    # Only allow in debug mode
    if not settings.DEBUG:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    _ensure_user_store()
    user_store = user_store_module.user_store
    if user_store is None:
        return {
            "error": "User store not initialized",
            "user_store_initialized": False,
        }

    # Get user by email or user_id
    user = None
    if email:
        user = await user_store.get_by_email(email)
    elif user_id:
        user = await user_store.get_by_id(user_id)
    else:
        return {
            "error": "Either email or user_id must be provided",
        }

    if not user:
        return {
            "error": "User not found",
            "email": email,
            "user_id": user_id,
        }

    # Check account existence
    from app.core.account_store import MongoDBAccountStore

    account_store = get_account_store()
    account_exists = False
    account_info = None
    available_account_ids = []

    if user.account_id and account_store:
        if isinstance(account_store, MongoDBAccountStore):
            account = await account_store._get_by_id_async(user.account_id)
            if account:
                account_exists = True
                account_info = {
                    "id": account.id,
                    "name": account.name,
                }
            # Get all accounts for debugging
            try:
                all_accounts = await account_store._list_accounts_async()
                available_account_ids = [t.id for t in all_accounts] if all_accounts else []
            except Exception as e:
                logging.error(f"Could not list accounts: {e}")
        else:
            account = account_store.get_by_id(user.account_id)
            if account:
                account_exists = True
                account_info = {
                    "id": account.id,
                    "name": account.name,
                }

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "email_verified": user.email_verified,
            "account_id": user.account_id,
            "role": user.role,
            "created_at": str(user.created_at),
        },
        "account": {
            "exists": account_exists,
            "info": account_info,
        },
        "available_account_ids": available_account_ids,
        "diagnosis": {
            "has_account_id": user.account_id is not None,
            "account_exists": account_exists,
            "email_verified": user.email_verified,
            "can_login": user.email_verified and account_exists,
        },
    }
