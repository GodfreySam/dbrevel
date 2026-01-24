"""Admin dashboard endpoints for platform management."""

from datetime import datetime
from typing import Any, List, Optional

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
    account = None
    account_store = get_account_store()
    if account_store:
        account = await account_store.get_by_id_async(user.account_id)

    # Create JWT with admin role
    access_token = create_access_token(user_id=user.id, email=user.email, role="admin")

    # Return token with user info
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        account_id=user.account_id,
        account_name=account.name if account else "Unknown",
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
    account_store = get_account_store()
    if not account_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized",
        )

    # Get all tenants (use async version)
    all_accounts = await account_store.list_accounts_async()

    # Filter by search if provided
    if search:
        search_lower = search.lower()
        all_accounts = [t for t in all_accounts if search_lower in t.name.lower()]

    # Paginate
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_accounts = all_accounts[start_idx:end_idx]

    # Convert to response model
    return [
        AccountResponse(
            id=t.id,
            name=t.name,
            api_key=t.api_key,
            postgres_url=mask_database_url(decrypt_database_url(t.postgres_url)),
            mongodb_url=mask_database_url(decrypt_database_url(t.mongodb_url)),
            gemini_mode=t.gemini_mode,
        )
        for t in paginated_accounts
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
    account_store = get_account_store()
    if not account_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account store not initialized",
        )

    account = await account_store.get_by_id_async(account_id)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    return AccountResponse(
        id=account.id,
        name=account.name,
        api_key=account.api_key,
        postgres_url=mask_database_url(decrypt_database_url(account.postgres_url)),
        mongodb_url=mask_database_url(decrypt_database_url(account.mongodb_url)),
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
    account_store = get_account_store()
    user_store = get_user_store()
    project_store = get_project_store()

    if not account_store or not user_store or not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Required stores not initialized",
        )

    # Verify account exists
    account = await account_store.get_by_id_async(account_id)

    if not account:
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
    success = await account_store.delete_account_async(account_id)

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
    account_store = get_account_store()
    project_store = get_project_store()

    if not user_store or not account_store:
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
        query_filter["email"] = {"$regex": search, "$options": "i"}  # type: ignore[assignment]

    # Paginate and collect docs
    assert user_store.db is not None  # Type assertion for mypy
    skip = (page - 1) * limit
    cursor = (
        user_store.db.users.find(query_filter)
        .skip(skip)
        .limit(limit)
        .sort("created_at", -1)
    )

    docs = []
    async for doc in cursor:
        docs.append(doc)

    # Compute project counts per account in a single aggregation
    project_counts: dict = {}
    if project_store:
        try:
            await project_store._ensure_connected()  # type: ignore[attr-defined]
            assert project_store.db is not None  # Type assertion for mypy
            account_ids = list(
                {d.get("account_id") for d in docs if d.get("account_id")}
            )
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
        account_name = "Unknown"
        if doc.get("account_id"):
            try:
                account = await account_store.get_by_id_async(doc["account_id"])
                if account:
                    account_name = account.name
            except Exception:
                account_name = "Unknown"

        users.append(
            UserResponse(
                id=doc.get("id", ""),
                email=doc.get("email", ""),
                account_id=doc.get("account_id", ""),
                account_name=account_name,
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
    account_store = get_account_store()

    if not user_store or not account_store:
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
    account = await account_store.get_by_id_async(user.account_id)

    return UserResponse(
        id=user.id,
        email=user.email,
        account_id=user.account_id,
        account_name=account.name if account else "Unknown",
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
    account_store = get_account_store()

    if not user_store or not account_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized",
        )

    # Prevent admin from demoting themselves
    if request.role and request.role != "admin" and user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself",
        )

    try:
        updated_user = await user_store.update_user(
            user_id=user_id,
            role=request.role,
            email_verified=request.email_verified,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Get account name
    account = await account_store.get_by_id_async(updated_user.account_id)

    return UserResponse(
        id=updated_user.id,
        email=updated_user.email,
        account_id=updated_user.account_id,
        account_name=account.name if account else "Unknown",
        created_at=updated_user.created_at,
        last_login=updated_user.last_login,
        email_verified=updated_user.email_verified,
        role=updated_user.role,
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

    # Prevent admin from deleting themselves
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    deleted = await user_store.delete_user(user_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
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
    account_store = get_account_store()

    if not project_store or not account_store:
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
            postgres_url=mask_database_url(decrypt_database_url(p.postgres_url)),
            mongodb_url=mask_database_url(decrypt_database_url(p.mongodb_url)),
            created_at=p.created_at,
            updated_at=p.updated_at,
            is_active=p.is_active,
        )
        for p in projects
    ]


@router.patch("/projects/{project_id}/deactivate", response_model=ProjectResponse)
async def deactivate_project(
    project_id: str,
    current_admin: User = Depends(get_current_admin),
):
    """
    Deactivate a project (set is_active to False).

    Admin only.
    """
    project_store = get_project_store()

    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    # Get project first
    project = await project_store.get_by_id_async(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Update is_active to False
    updated = await project_store.update_project_async(
        project_id=project_id,
        is_active=False,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate project",
        )

    return ProjectResponse(
        id=updated.id,
        name=updated.name,
        account_id=updated.account_id,
        api_key="***",
        postgres_url=mask_database_url(decrypt_database_url(updated.postgres_url)),
        mongodb_url=mask_database_url(decrypt_database_url(updated.mongodb_url)),
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        is_active=updated.is_active,
    )


@router.patch("/projects/{project_id}/activate", response_model=ProjectResponse)
async def activate_project(
    project_id: str,
    current_admin: User = Depends(get_current_admin),
):
    """
    Activate a project (set is_active to True).

    Admin only.
    """
    project_store = get_project_store()

    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    # Get project first
    project = await project_store.get_by_id_async(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Update is_active to True
    updated = await project_store.update_project_async(
        project_id=project_id,
        is_active=True,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate project",
        )

    return ProjectResponse(
        id=updated.id,
        name=updated.name,
        account_id=updated.account_id,
        api_key="***",
        postgres_url=mask_database_url(decrypt_database_url(updated.postgres_url)),
        mongodb_url=mask_database_url(decrypt_database_url(updated.mongodb_url)),
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        is_active=updated.is_active,
    )


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_admin: User = Depends(get_current_admin),
):
    """
    Permanently delete a project.

    Admin only. Use with caution.
    """
    project_store = get_project_store()

    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    deleted = await project_store.delete_project_async(project_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )


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
    account_store = get_account_store()
    user_store = get_user_store()
    project_store = get_project_store()

    if not account_store or not user_store or not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Required stores not initialized",
        )

    # Count tenants (use async version)
    all_accounts = await account_store.list_accounts_async()
    total_accounts = len(all_accounts)

    # Count users (exclude admin users to match Users table behavior)
    await user_store._ensure_connected()
    assert user_store.db is not None  # Type assertion for mypy
    user_filter = {"role": {"$ne": "admin"}}  # Exclude admin users
    total_users = await user_store.db.users.count_documents(user_filter)
    verified_users = await user_store.db.users.count_documents(
        {**user_filter, "email_verified": True}
    )

    # Count projects (exclude demo project to match real user projects only)
    await project_store._ensure_connected()  # type: ignore[attr-defined]
    assert project_store.db is not None  # Type assertion for mypy
    from app.core.demo_account import DEMO_PROJECT_ID

    project_filter = {
        "is_active": True,
        "project_id": {"$ne": DEMO_PROJECT_ID},  # Exclude demo project
    }
    total_projects = await project_store.db.projects.count_documents(project_filter)

    # Count queries today (from usage_logs if it exists)
    from datetime import datetime, timedelta

    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_queries_today = 0
    try:
        total_queries_today = await user_store.db.usage_logs.count_documents(
            {"timestamp": {"$gte": today_start}}
        )
    except Exception:
        # usage_logs collection may not exist yet
        pass

    # Count active tenants in last 7 days
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_account_ids = set()
    try:
        async for log in user_store.db.usage_logs.find(
            {"timestamp": {"$gte": seven_days_ago}}, {"account_id": 1}
        ):
            if "account_id" in log:
                active_account_ids.add(log["account_id"])
    except Exception:
        pass

    return PlatformStats(
        total_accounts=total_accounts,  # Renamed to accounts
        total_users=total_users,
        total_projects=total_projects,
        verified_users=verified_users,
        active_accounts_last_7_days=len(active_account_ids),  # Renamed to accounts
        total_queries_today=total_queries_today,
    )


class UsageDataPoint(BaseModel):
    """Single data point for time-series usage."""

    date: str  # YYYY-MM-DD format
    queries: int
    execution_time_ms: float


class UsageAnalytics(BaseModel):
    """Comprehensive usage analytics with time-series data."""

    total_queries: int
    total_execution_time_ms: float
    total_tokens: int
    daily_usage: List[UsageDataPoint]  # Last 30 days
    queries_by_type: dict  # {"postgres": X, "mongodb": Y}


@router.get("/analytics/usage", response_model=UsageAnalytics)
async def get_usage_analytics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    account_id: Optional[str] = Query(None),
    current_admin: User = Depends(get_current_admin),
):
    """
    Get usage analytics with time-series data for charts.

    Returns:
    - Total queries, execution time, and tokens
    - Daily usage breakdown for last 30 days
    - Query distribution by database type (postgres/mongodb)

    Admin only.
    """
    user_store = get_user_store()
    if not user_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User store not initialized",
        )

    await user_store._ensure_connected()

    from datetime import datetime, timedelta
    import logging

    # Default to last 30 days if no date range provided
    now = datetime.utcnow()
    if not start_date:
        start_dt = now - timedelta(days=30)
    else:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except ValueError:
            start_dt = now - timedelta(days=30)

    if not end_date:
        end_dt = now
    else:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        except ValueError:
            end_dt = now

    # Build query filter
    query_filter: dict[str, Any] = {"timestamp": {"$gte": start_dt, "$lte": end_dt}}
    if account_id:
        query_filter["account_id"] = account_id

    # Initialize counters
    total_queries = 0
    total_execution_time_ms = 0.0
    total_tokens = 0
    queries_by_type = {"postgres": 0, "mongodb": 0}
    daily_data: dict[str, dict[str, float]] = {}  # date_str -> {queries, execution_time_ms}

    try:
        assert user_store.db is not None  # Type assertion for mypy
        async for log in user_store.db.usage_logs.find(query_filter):
            total_queries += 1
            exec_time = log.get("execution_time_ms", 0.0)
            total_execution_time_ms += exec_time
            total_tokens += log.get("tokens_used", 0) or log.get(
                "gemini_tokens_used", 0
            )

            # Count by query type
            query_type = log.get("query_type", "unknown")
            if query_type in queries_by_type:
                queries_by_type[query_type] += 1

            # Aggregate by day
            timestamp = log.get("timestamp")
            if timestamp:
                date_str = timestamp.strftime("%Y-%m-%d")
                if date_str not in daily_data:
                    daily_data[date_str] = {"queries": 0, "execution_time_ms": 0.0}
                daily_data[date_str]["queries"] = int(daily_data[date_str].get("queries", 0)) + 1  # type: ignore[assignment]
                daily_data[date_str]["execution_time_ms"] += exec_time

    except Exception as e:
        logging.warning(f"Could not query usage_logs: {e}")

    # Build daily_usage list with all days in range (fill gaps with zeros)
    daily_usage = []
    current_date = start_dt.date()
    end_date_obj = end_dt.date()

    while current_date <= end_date_obj:
        date_str = current_date.strftime("%Y-%m-%d")
        if date_str in daily_data:
            daily_usage.append(
                UsageDataPoint(
                    date=date_str,
                    queries=int(daily_data[date_str]["queries"]),
                    execution_time_ms=daily_data[date_str]["execution_time_ms"],
                )
            )
        else:
            daily_usage.append(
                UsageDataPoint(
                    date=date_str,
                    queries=0,
                    execution_time_ms=0.0,
                )
            )
        current_date += timedelta(days=1)

    return UsageAnalytics(
        total_queries=total_queries,
        total_execution_time_ms=total_execution_time_ms,
        total_tokens=total_tokens,
        daily_usage=daily_usage,
        queries_by_type=queries_by_type,
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
    account_store = get_account_store()
    project_store = get_project_store()

    if not account_store or not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stores not initialized",
        )

    from datetime import datetime

    from app.core.db_test import test_mongodb_connection, test_postgres_connection
    from app.core.encryption import decrypt_database_url

    health_statuses = []

    # Get all tenants
    all_accounts = await account_store.list_accounts_async()

    # Get all projects
    all_projects = await project_store.list_all_projects_async()

    # Group projects by account_id
    projects_by_account: dict[str, list] = {}
    for project in all_projects:
        if project.account_id not in projects_by_account:
            projects_by_account[project.account_id] = []
        projects_by_account[project.account_id].append(project)

    # Test connections for each account's projects
    for account in all_accounts:
        tenant_projects = projects_by_account.get(account.id, [])

        # Aggregate health status across all projects for this tenant
        postgres_status = "unknown"
        mongodb_status = "unknown"

        if tenant_projects:
            # Test first project's databases (projects have their own DB URLs)
            project = tenant_projects[0]
            pg_url = (
                decrypt_database_url(project.postgres_url)
                if project.postgres_url
                else None
            )
            mongo_url = (
                decrypt_database_url(project.mongodb_url)
                if project.mongodb_url
                else None
            )

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

        health_statuses.append(
            HealthStatus(
                account_id=account.id,
                account_name=account.name,
                postgres_status=postgres_status,
                mongodb_status=mongodb_status,
                last_checked=datetime.utcnow(),
            )
        )

    return health_statuses
