"""Project management endpoints for users."""

from datetime import datetime
from typing import List

from app.core.account_keys import generate_account_key
from app.core.auth import get_current_user
from app.core.encryption import (
    decrypt_database_url,
    encrypt_database_url,
    mask_database_url,
)
from app.core.project_store import generate_project_id, get_project_store
from app.models.project import (
    ProjectApiKeyRevealResponse,
    ProjectApiKeyRotateResponse,
    ProjectConnectionTestRequest,
    ProjectConnectionTestResponse,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()

# Test endpoint to verify routing works


@router.get("/test-ping")
async def test_ping():
    """Simple test endpoint to verify routing works"""
    return {"status": "ok", "message": "Test endpoint is working"}


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new project under the current user's account.

    Each project gets its own unique API key and database configurations.
    """
    project_store = get_project_store()
    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    # Generate unique project ID and API key
    project_id = generate_project_id()
    api_key = generate_account_key()

    # Handle both old format (postgres_url/mongodb_url) and new format (databases array)
    # Convert new format to old format for backward compatibility with store
    postgres_url = request.postgres_url
    mongodb_url = request.mongodb_url

    # If new format is provided, extract postgres and mongodb URLs
    if request.databases:
        for db in request.databases:
            db_type = db.get("type", "").lower()
            db_url = db.get("connection_url", "").strip()
            if db_type == "postgres" and db_url:
                postgres_url = db_url
            elif db_type == "mongodb" and db_url:
                mongodb_url = db_url

    # Encrypt database URLs at the API layer
    encrypted_postgres_url = encrypt_database_url(postgres_url) if postgres_url else ""
    encrypted_mongodb_url = encrypt_database_url(mongodb_url) if mongodb_url else ""

    # Create project (store still uses old format, but we'll add databases field in future)
    project = await project_store.create_project_async(
        name=request.name,
        account_id=current_user.account_id,
        api_key=api_key,
        postgres_url=encrypted_postgres_url,
        mongodb_url=encrypted_mongodb_url,
        project_id=project_id,
    )

    # Mask databases array
    masked_databases = []
    if project.databases:
        for db_config in project.databases:
            try:
                decrypted_url = decrypt_database_url(db_config.connection_url)
                masked_databases.append(
                    {
                        "type": db_config.type,
                        "connection_url": mask_database_url(decrypted_url),
                    }
                )
            except Exception:
                # If decryption fails, still include the type with masked URL
                masked_databases.append(
                    {"type": db_config.type, "connection_url": "***"}
                )

    # Return response with unmasked API key (only on creation)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        account_id=project.account_id,
        api_key=project.api_key,  # Show full API key on creation
        postgres_url=(
            mask_database_url(decrypt_database_url(project.postgres_url))
            if project.postgres_url
            else ""
        ),
        mongodb_url=(
            mask_database_url(decrypt_database_url(project.mongodb_url))
            if project.mongodb_url
            else ""
        ),
        databases=masked_databases,
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_active=project.is_active,
    )


@router.get("", response_model=List[ProjectListResponse])
async def list_projects(
    current_user: User = Depends(get_current_user),
):
    """
    List all projects for the current user's account.

    Returns a simplified list without sensitive data.
    """
    project_store = get_project_store()
    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    projects = await project_store.list_by_account_async(current_user.account_id)

    return [
        ProjectListResponse(
            id=p.id,
            name=p.name,
            is_active=p.is_active,
            created_at=p.created_at,
        )
        for p in projects
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information about a specific project.

    User must own the project (belongs to their tenant).
    """
    project_store = get_project_store()
    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    project = await project_store.get_by_id_async(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Verify project belongs to user's account
    if project.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project",
        )

    # Mask databases array
    masked_databases = []
    if project.databases:
        for db_config in project.databases:
            try:
                decrypted_url = decrypt_database_url(db_config.connection_url)
                masked_databases.append(
                    {
                        "type": db_config.type,
                        "connection_url": mask_database_url(decrypted_url),
                    }
                )
            except Exception:
                # If decryption fails, still include the type with masked URL
                masked_databases.append(
                    {"type": db_config.type, "connection_url": "***"}
                )

    return ProjectResponse(
        id=project.id,
        name=project.name,
        account_id=project.account_id,
        api_key="***",  # Mask API key on retrieval for security
        postgres_url=(
            mask_database_url(decrypt_database_url(project.postgres_url))
            if project.postgres_url
            else ""
        ),
        mongodb_url=(
            mask_database_url(decrypt_database_url(project.mongodb_url))
            if project.mongodb_url
            else ""
        ),
        databases=masked_databases,
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_active=project.is_active,
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Update a project's configuration.

    User must own the project (belongs to their tenant).
    """
    project_store = get_project_store()
    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    # Verify project exists and belongs to user
    project = await project_store.get_by_id_async(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project",
        )

    # Update project - handle both old and new format
    updates = {}
    if request.name is not None:
        updates["name"] = request.name

    # Handle old format (postgres_url/mongodb_url)
    postgres_url = request.postgres_url
    mongodb_url = request.mongodb_url

    # If new format (databases) is provided, extract postgres and mongodb URLs
    if request.databases is not None:
        # Clear existing URLs first
        postgres_url = ""
        mongodb_url = ""
        # Extract from databases array
        for db in request.databases:
            db_type = db.get("type", "").lower()
            db_url = db.get("connection_url", "").strip()
            if db_type == "postgres" and db_url:
                postgres_url = db_url
            elif db_type == "mongodb" and db_url:
                mongodb_url = db_url

    # Update with extracted/legacy URLs
    if postgres_url is not None:
        updates["postgres_url"] = (
            encrypt_database_url(postgres_url) if postgres_url else ""
        )
    if mongodb_url is not None:
        updates["mongodb_url"] = (
            encrypt_database_url(mongodb_url) if mongodb_url else ""
        )

    updated_project = await project_store.update_project_async(project_id, **updates)

    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project",
        )

    # Mask databases array
    masked_databases = []
    if updated_project.databases:
        for db_config in updated_project.databases:
            try:
                decrypted_url = decrypt_database_url(db_config.connection_url)
                masked_databases.append(
                    {
                        "type": db_config.type,
                        "connection_url": mask_database_url(decrypted_url),
                    }
                )
            except Exception:
                # If decryption fails, still include the type with masked URL
                masked_databases.append(
                    {"type": db_config.type, "connection_url": "***"}
                )

    return ProjectResponse(
        id=updated_project.id,
        name=updated_project.name,
        account_id=updated_project.account_id,
        api_key="***",  # Mask API key
        postgres_url=(
            mask_database_url(decrypt_database_url(updated_project.postgres_url))
            if updated_project.postgres_url
            else ""
        ),
        mongodb_url=(
            mask_database_url(decrypt_database_url(updated_project.mongodb_url))
            if updated_project.mongodb_url
            else ""
        ),
        databases=masked_databases,
        created_at=updated_project.created_at,
        updated_at=updated_project.updated_at,
        is_active=updated_project.is_active,
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Soft delete a project (sets is_active=False).

    User must own the project (belongs to their tenant).
    """
    project_store = get_project_store()
    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    # Verify project exists and belongs to user
    project = await project_store.get_by_id_async(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project",
        )

    # Soft delete
    success = await project_store.delete_project_async(project_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project",
        )


@router.post("/{project_id}/rotate-key", response_model=ProjectApiKeyRotateResponse)
async def rotate_project_api_key(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Rotate a project's API key.

    The old key will be immediately invalidated.
    User must own the project (belongs to their tenant).
    """
    project_store = get_project_store()
    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    # Verify project exists and belongs to user
    project = await project_store.get_by_id_async(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project",
        )

    # Generate new API key
    new_api_key = generate_account_key()

    # Rotate key
    old_key_hash = await project_store.rotate_api_key_async(project_id, new_api_key)

    if not old_key_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rotate API key",
        )

    return ProjectApiKeyRotateResponse(
        project_id=project_id,
        new_api_key=new_api_key,
        rotated_at=datetime.utcnow(),
    )


@router.get("/{project_id}/api-key", response_model=ProjectApiKeyRevealResponse)
async def reveal_project_api_key(
    project_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Reveal a project's API key.

    User must own the project (belongs to their tenant).
    This endpoint allows users to see their API key after creation.
    """
    project_store = get_project_store()
    if not project_store:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project store not initialized",
        )

    project = await project_store.get_by_id_async(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Verify project belongs to user's account
    if project.account_id != current_user.account_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this project",
        )

    # Return the actual API key (stored in plain text in database for lookup)
    return ProjectApiKeyRevealResponse(
        project_id=project_id,
        api_key=project.api_key,
    )


@router.post("/test-connection", response_model=ProjectConnectionTestResponse)
async def test_database_connections(
    request: ProjectConnectionTestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Test database connections for a project.

    If project_id is provided, uses the project's saved database URLs.
    Otherwise, uses the provided postgres_url and/or mongodb_url directly.
    """
    import logging

    logger = logging.getLogger(__name__)
    from app.core.db_test import (
        test_mongodb_connection_lightweight,
        test_postgres_connection_lightweight,
    )

    project_store = get_project_store()
    postgres_url = request.postgres_url
    mongodb_url = request.mongodb_url

    if request.project_id:
        if not project_store:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Project store not initialized",
            )
        project = await project_store.get_by_id_async(request.project_id)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        if project.account_id != current_user.account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project",
            )
        if project.databases:
            for db_config in project.databases:
                db_type = db_config.type.lower()
                db_url = db_config.connection_url
                if db_url and db_url.strip() and not db_url.startswith("***"):
                    try:
                        decrypted_url = decrypt_database_url(db_url)
                        if db_type == "postgres" and not postgres_url:
                            postgres_url = decrypted_url
                        elif db_type == "mongodb" and not mongodb_url:
                            mongodb_url = decrypted_url
                    except Exception as e:
                        logger.warning(
                            "Failed to decrypt %s URL from databases array for project %s: %s",
                            db_type,
                            project.id,
                            e,
                        )
        if (
            not postgres_url
            and project.postgres_url
            and project.postgres_url.strip()
            and not project.postgres_url.startswith("***")
        ):
            try:
                postgres_url = decrypt_database_url(project.postgres_url)
            except Exception as e:
                logger.warning(
                    "Failed to decrypt postgres_url for project %s: %s", project.id, e
                )
                postgres_url = None
        if (
            not mongodb_url
            and project.mongodb_url
            and project.mongodb_url.strip()
            and not project.mongodb_url.startswith("***")
        ):
            try:
                mongodb_url = decrypt_database_url(project.mongodb_url)
            except Exception as e:
                logger.warning(
                    "Failed to decrypt mongodb_url for project %s: %s", project.id, e
                )
                mongodb_url = None

    results = ProjectConnectionTestResponse()

    if postgres_url:
        safe_url = postgres_url.split("@")[-1] if "@" in postgres_url else postgres_url
        logger.info(
            "Testing PostgreSQL connection for project %s: ...@%s",
            request.project_id,
            safe_url,
        )
        try:
            pg_result = await test_postgres_connection_lightweight(postgres_url)
            results.postgres = pg_result.to_dict()
            logger.info("PostgreSQL test completed: success=%s", pg_result.success)
        except Exception as e:
            logger.error("PostgreSQL test failed: %s", e, exc_info=True)
            results.postgres = {"success": False, "error": str(e)}

    if mongodb_url:
        logger.info("Testing MongoDB connection")
        try:
            # Use lightweight test for consistency with PostgreSQL (fast feedback)
            mongo_result = await test_mongodb_connection_lightweight(mongodb_url)
            results.mongodb = mongo_result.to_dict()
            logger.info("MongoDB test completed: success=%s", mongo_result.success)
        except Exception as e:
            logger.error("MongoDB test failed: %s", e, exc_info=True)
            results.mongodb = {"success": False, "error": str(e)}

    if not postgres_url and not mongodb_url:
        logger.warning("No database URLs available to test")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No database URLs available to test. Either provide project_id or postgres_url/mongodb_url",
        )

    logger.info(
        "Test connection completed: postgres=%s mongodb=%s",
        bool(results.postgres),
        bool(results.mongodb),
    )
    return results
