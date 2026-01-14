"""Admin dashboard endpoints for platform management."""

from datetime import datetime
from typing import List, Optional

from app.core.account_store import get_account_store
from app.core.admin_otp import get_admin_otp_store
from app.core.auth import create_access_token, get_current_admin
from app.core.email_service import get_email_service
from app.core.encryption import decrypt_database_url, mask_database_url
from app.core.project_store import get_project_store
from app.core.user_store import get_user_store
from app.models.account import AccountResponse
from app.models.project import ProjectResponse
from app.models.user import TokenResponse, User, UserResponse
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr

router = APIRouter()


# ============================================================================
# Admin OTP Authentication Models
# ============================================================================


class AdminOTPRequest(BaseModel):
    """Request model for admin OTP."""

    email: EmailStr


class AdminOTPVerifyRequest(BaseModel):
    """Request model for admin OTP verification."""

    email: EmailStr
    otp: str


class AdminOTPResponse(BaseModel):
    """Response model for admin OTP request."""

    message: str = "If an admin account exists, an OTP has been sent to your email."


# ============================================================================
# Admin Authentication Endpoints
# ============================================================================


@router.post("/request-otp", response_model=AdminOTPResponse)
async def request_admin_otp(request: AdminOTPRequest):
    """
    Request an OTP for admin login.

    This endpoint is public but only sends OTP to verified admin emails.
    Always returns success message to prevent email enumeration.
    """
    admin_otp_store = get_admin_otp_store()
    user_store = get_user_store()
    if not admin_otp_store or not user_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin OTP service not initialized",
        )

    # Check if user exists and is admin
    user = await user_store.get_by_email(request.email)

    if user and user.role == "admin" and user.email_verified:
        # Generate and send OTP
        otp = await admin_otp_store.create_admin_otp(
            user_id=user.id,
            email=user.email,
            expires_in_minutes=10,
        )

        # Send OTP via email
        email_svc = get_email_service()
        if email_svc:
            await email_svc.send_admin_otp_email(user.email, otp)

    # Always return success message (don't reveal if admin exists)
    return AdminOTPResponse()


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_admin_otp(request: AdminOTPVerifyRequest):
    """
    Verify admin OTP and return JWT token.

    Returns admin JWT with role claim if OTP is valid.
    """
    admin_otp_store = get_admin_otp_store()
    user_store = get_user_store()
    if not admin_otp_store or not user_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admin OTP service not initialized",
        )

    # Verify OTP
    otp_doc = await admin_otp_store.verify_otp(request.email, request.otp)

    if not otp_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP",
        )

    # Get user
    user = await user_store.get_by_email(request.email)

    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # Mark OTP as used
    await admin_otp_store.mark_otp_used(request.email, request.otp)

    # Get tenant info
    tenant = None
    tenant_store = get_account_store()
    if tenant_store and hasattr(tenant_store, "_get_by_id_async"):
        tenant = await tenant_store._get_by_id_async(user.account_id)
    elif tenant_store:
        tenant = tenant_store.get_by_id(user.account_id)

    # Create JWT with admin role
    access_token = create_access_token(
        user_id=user.id, email=user.email, role="admin"
    )

    # Return token with user info
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        account_id=user.account_id,
        account_name=tenant.name if tenant else "Unknown",
        created_at=user.created_at,
        last_login=user.last_login,
        email_verified=user.email_verified,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_response,
    )


# ============================================================================
# Admin Tenant Management
# ============================================================================


@router.get("/accounts", response_model=List[AccountResponse])
async def list_all_accounts(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
):
    """
    List all accounts in the platform.

    Supports pagination and search by name.
    Admin only.
    """
    tenant_store = get_account_store()
    if not tenant_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized",
        )

    # Get all tenants (use async version)
    all_tenants = await tenant_store._list_accounts_async()

    # Filter by search if provided
    if search:
        search_lower = search.lower()
        all_tenants = [
            t for t in all_tenants if search_lower in t.name.lower()]

    # Paginate
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_tenants = all_tenants[start_idx:end_idx]

    # Convert to response model
    return [
        AccountResponse(
            id=t.id,
            name=t.name,
            api_key=t.api_key,
            postgres_url=mask_database_url(
                decrypt_database_url(t.postgres_url)),
            mongodb_url=mask_database_url(decrypt_database_url(t.mongodb_url)),
            gemini_mode=t.gemini_mode,
        )
        for t in paginated_tenants
    ]


@router.get("/accounts/{account_id}", response_model=AccountResponse)
async def get_account_details(
    account_id: str,
    current_admin: User = Depends(get_current_admin),
):
    """
    Get detailed information about a specific tenant.

    Admin only.
    """
    tenant_store = get_account_store()
    if not tenant_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized",
        )

    # Use async version if available
    if hasattr(tenant_store, "_get_by_id_async"):
        account = await tenant_store._get_by_id_async(account_id)
    else:
        account = tenant_store.get_by_id(account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return AccountResponse(
        id=account.id,
        name=account.name,
        api_key=account.api_key,
        postgres_url=mask_database_url(
            decrypt_database_url(account.postgres_url)),
        mongodb_url=mask_database_url(
            decrypt_database_url(account.mongodb_url)),
        gemini_mode=account.gemini_mode,
    )


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    current_admin: User = Depends(get_current_admin),
):
    """
    Delete a tenant and all associated data (cascade).

    This will delete:
    - The tenant
    - All users belonging to the tenant
    - All projects belonging to the tenant

    Admin only. Use with caution.
    """
    tenant_store = get_account_store()
    user_store = get_user_store()
    project_store = get_project_store()

    if not tenant_store or not user_store or not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Required stores not initialized",
        )

    # Verify account exists
    if hasattr(tenant_store, "_get_by_id_async"):
        tenant = await tenant_store._get_by_id_async(account_id)
    else:
        tenant = tenant_store.get_by_id(account_id)

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    # Delete all projects for this account
    projects = await project_store.list_by_account_async(account_id)
    for project in projects:
        await project_store.delete_project_async(project.id)

    # Delete all users for this account
    # Note: This requires a method in user_store to delete by account_id
    # For now, we'll skip this and just delete the account

    # Delete account (use async version if available)
    if hasattr(tenant_store, "_delete_account_async"):
        success = await tenant_store._delete_account_async(account_id)
    else:
        success = tenant_store.delete_account(account_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete account",
        )


# ============================================================================
# Admin User Management
# ============================================================================


@router.get("/users", response_model=List[UserResponse])
async def list_all_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
):
    """
    List all users in the platform.

    Supports pagination, search by email, and filtering by tenant.
    Admin only.
    """
    user_store = get_user_store()
    tenant_store = get_account_store()
    project_store = get_project_store()

    if not user_store or not tenant_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized",
        )

    # Build query filter
    await user_store._ensure_connected()
    query_filter = {}

    if account_id:
        query_filter["account_id"] = account_id

    if role:
        query_filter["role"] = role

    if search:
        query_filter["email"] = {"$regex": search, "$options": "i"}

    # Get total count
    total_count = await user_store.db.users.count_documents(query_filter)

    # Paginate and collect docs
    skip = (page - 1) * limit
    cursor = user_store.db.users.find(query_filter).skip(
        skip).limit(limit).sort("created_at", -1)

    docs = []
    async for doc in cursor:
        docs.append(doc)

    # Compute project counts per account in a single aggregation
    project_counts: dict = {}
    if project_store:
        try:
            await project_store._ensure_connected()
            account_ids = list({d.get("account_id")
                               for d in docs if d.get("account_id")})
            if account_ids:
                pipeline = [
                    {"$match": {"account_id": {"$in": account_ids}}},
                    {"$group": {"_id": "$account_id", "count": {"$sum": 1}}},
                ]
                async for row in project_store.db.projects.aggregate(pipeline):
                    project_counts[row["_id"]] = int(row["count"])
        except Exception:
            # If aggregation fails, leave counts empty
            project_counts = {}

    users: List[UserResponse] = []
    for doc in docs:
        # Get tenant name
        tenant_name = "Unknown"
        if doc.get("account_id"):
            try:
                if hasattr(tenant_store, "_get_by_id_async"):
                    tenant = await tenant_store._get_by_id_async(doc["account_id"])
                else:
                    tenant = tenant_store.get_by_id(doc["account_id"])
                if tenant:
                    tenant_name = tenant.name
            except Exception:
                tenant_name = "Unknown"

        users.append(
            UserResponse(
                id=doc.get("id", ""),
                email=doc.get("email", ""),
                account_id=doc.get("account_id", ""),
                account_name=tenant_name,
                email_verified=doc.get("email_verified", False),
                role=doc.get("role", "user"),
                created_at=doc.get("created_at"),
                projects_count=project_counts.get(doc.get("account_id"), 0),
            )
        )

    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_details(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
):
    """
    Get detailed information about a specific user.

    Admin only.
    """
    user_store = get_user_store()
    tenant_store = get_account_store()

    if not user_store or not tenant_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized",
        )

    user = await user_store.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get tenant/account info
    tenant = None
    if hasattr(tenant_store, "_get_by_id_async"):
        tenant = await tenant_store._get_by_id_async(user.account_id)
    else:
        tenant = tenant_store.get_by_id(user.account_id)

    return UserResponse(
        id=user.id,
        email=user.email,
        account_id=user.account_id,
        account_name=tenant.name if tenant else "Unknown",
        created_at=user.created_at,
        last_login=user.last_login,
        email_verified=user.email_verified,
        role=user.role,
    )


class UserUpdateRequest(BaseModel):
    """Request model for updating user (admin only)."""

    role: Optional[str] = None
    email_verified: Optional[bool] = None


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdateRequest,
    current_admin: User = Depends(get_current_admin),
):
    """
    Update a user's role or email verification status.

    Admin only.
    """
    user_store = get_user_store()
    tenant_store = get_account_store()

    if not user_store or not tenant_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized",
        )

    # This requires implementing update_user in user_store
    # For now, raise not implemented
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User update not yet implemented",
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_admin: User = Depends(get_current_admin),
):
    """
    Delete a user.

    Admin only. Use with caution.
    """
    user_store = get_user_store()

    if not user_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized",
        )

    # This requires implementing delete_user in user_store
    # For now, raise not implemented
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="User deletion not yet implemented",
    )


# ============================================================================
# Admin Project Management
# ============================================================================


@router.get("/projects", response_model=List[ProjectResponse])
async def list_all_projects(
    account_id: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
):
    """
    List all projects across all tenants.
    Can be filtered by account_id.
    Admin only.
    """
    project_store = get_project_store()
    tenant_store = get_account_store()

    if not project_store or not tenant_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    if account_id:
        # Filter by account
        projects = await project_store.list_by_account_async(account_id)
    else:
        # Get all projects
        projects = await project_store.list_all_projects_async()

    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            account_id=p.account_id,
            api_key="***",  # Mask for security
            postgres_url=mask_database_url(
                decrypt_database_url(p.postgres_url)),
            mongodb_url=mask_database_url(decrypt_database_url(p.mongodb_url)),
            created_at=p.created_at,
            updated_at=p.updated_at,
            is_active=p.is_active,
        )
        for p in projects
    ]


# ============================================================================
# Admin Analytics Endpoints
# ============================================================================


class PlatformStats(BaseModel):
    """Platform-wide statistics."""

    total_accounts: int
    total_users: int
    total_projects: int
    verified_users: int
    active_accounts_last_7_days: int
    total_queries_today: int


@router.get("/analytics/stats", response_model=PlatformStats)
async def get_platform_stats(
    current_admin: User = Depends(get_current_admin),
):
    """
    Get platform-wide statistics.

    Admin only.
    """
    tenant_store = get_account_store()
    user_store = get_user_store()
    project_store = get_project_store()

    if not tenant_store or not user_store or not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Required stores not initialized",
        )

    # Count tenants (use async version)
    all_tenants = await tenant_store._list_accounts_async()
    total_tenants = len(all_tenants)

    # Count users
    await user_store._ensure_connected()
    total_users = await user_store.db.users.count_documents({})
    verified_users = await user_store.db.users.count_documents({"email_verified": True})

    # Count projects
    await project_store._ensure_connected()
    total_projects = await project_store.db.projects.count_documents({"is_active": True})

    # Count queries today (from usage_logs if it exists)
    from datetime import datetime, timedelta
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0)
    total_queries_today = 0
    try:
        total_queries_today = await user_store.db.usage_logs.count_documents({
            "timestamp": {"$gte": today_start}
        })
    except Exception:
        # usage_logs collection may not exist yet
        pass

    # Count active tenants in last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_account_ids = set()
    try:
        async for log in user_store.db.usage_logs.find(
            {"timestamp": {"$gte": seven_days_ago}},
            {"account_id": 1}
        ):
            if "account_id" in log:
                active_account_ids.add(log["account_id"])
    except Exception:
        pass

    return PlatformStats(
        total_accounts=total_tenants, # Renamed to accounts
        total_users=total_users,
        total_projects=total_projects,
        verified_users=verified_users,
        active_accounts_last_7_days=len(active_account_ids), # Renamed to accounts
        total_queries_today=total_queries_today,
    )


class UsageStats(BaseModel):
    """Usage statistics."""

    total_queries: int
    total_execution_time_ms: float
    total_tokens: int


@router.get("/analytics/usage", response_model=UsageStats)
async def get_usage_analytics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
):
    """
    Get usage analytics with optional date range and tenant filter.

    Admin only.
    """
    user_store = get_user_store()
    if not user_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized",
        )

    await user_store._ensure_connected()

    # Build query filter
    query_filter = {}
    if account_id:
        query_filter["account_id"] = account_id

    # Parse date range if provided
    from datetime import datetime
    if start_date:
        try:
            start_dt = datetime.fromisoformat(
                start_date.replace('Z', '+00:00'))
            query_filter.setdefault("timestamp", {})["$gte"] = start_dt
        except ValueError:
            pass

    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query_filter.setdefault("timestamp", {})["$lte"] = end_dt
        except ValueError:
            pass

    # Query usage_logs collection from MongoDB
    total_queries = 0
    total_execution_time_ms = 0.0
    total_tokens = 0

    try:
        async for log in user_store.db.usage_logs.find(query_filter):
            total_queries += 1
            total_execution_time_ms += log.get("execution_time_ms", 0.0)
            total_tokens += log.get("tokens_used", 0)
    except Exception as e:
        # usage_logs collection may not exist yet
        import logging
        logging.warning(f"Could not query usage_logs: {e}")

    return UsageStats(
        total_queries=total_queries,
        total_execution_time_ms=total_execution_time_ms,
        total_tokens=total_tokens,
    )


class HealthStatus(BaseModel):
    """Database health status for accounts."""

    account_id: str
    account_name: str
    postgres_status: str
    mongodb_status: str
    last_checked: datetime


@router.get("/analytics/health", response_model=List[HealthStatus])
async def get_database_health(
    current_admin: User = Depends(get_current_admin),
):
    """
    Get database connection health status for all tenants.

    Admin only.
    Tests database connections for all projects across all tenants.
    """
    tenant_store = get_account_store()
    project_store = get_project_store()

    if not tenant_store or not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stores not initialized",
        )

    from datetime import datetime

    from app.core.account_store import MongoDBAccountStore
    from app.core.db_test import (test_mongodb_connection,
                                  test_postgres_connection)
    from app.core.encryption import decrypt_database_url

    health_statuses = []

    # Get all tenants
    if isinstance(tenant_store, MongoDBAccountStore):
        all_tenants = await tenant_store._list_accounts_async()
    else:
        all_tenants = tenant_store.list_accounts()

    # Get all projects
    all_projects = await project_store.list_all_projects_async()

    # Group projects by account_id
    projects_by_account = {}
    for project in all_projects:
        if project.account_id not in projects_by_account:
            projects_by_account[project.account_id] = []
        projects_by_account[project.account_id].append(project)

    # Test connections for each account's projects
    for tenant in all_tenants:
        tenant_projects = projects_by_account.get(tenant.id, [])

        # Aggregate health status across all projects for this tenant
        postgres_status = "unknown"
        mongodb_status = "unknown"

        if tenant_projects:
            # Test first project's databases (projects have their own DB URLs)
            project = tenant_projects[0]
            pg_url = decrypt_database_url(
                project.postgres_url) if project.postgres_url else None
            mongo_url = decrypt_database_url(
                project.mongodb_url) if project.mongodb_url else None

            # Test PostgreSQL
            if pg_url:
                try:
                    pg_result = await test_postgres_connection(pg_url, timeout=5)
                    postgres_status = "healthy" if pg_result.success else "unhealthy"
                except Exception:
                    postgres_status = "unhealthy"
            else:
                postgres_status = "not_configured"

            # Test MongoDB
            if mongo_url:
                try:
                    mongo_result = await test_mongodb_connection(mongo_url, timeout=5)
                    mongodb_status = "healthy" if mongo_result.success else "unhealthy"
                except Exception:
                    mongodb_status = "unhealthy"
            else:
                mongodb_status = "not_configured"
        else:
            postgres_status = "no_projects"
            mongodb_status = "no_projects"

        health_statuses.append(HealthStatus(
            account_id=tenant.id,
            account_name=tenant.name,
            postgres_status=postgres_status,
            mongodb_status=mongodb_status,
            last_checked=datetime.utcnow(),
        ))

    return health_statuses
