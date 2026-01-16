"""Project management endpoints for users."""

from datetime import datetime
from typing import List

from app.core.account_keys import generate_account_key
from app.core.account_store import get_account_store
from app.core.auth import get_current_user
from app.core.encryption import decrypt_database_url, mask_database_url, encrypt_database_url
from app.core.project_store import generate_project_id, get_project_store
from app.models.project import (Project, ProjectApiKeyRevealResponse,
                                ProjectApiKeyRotateResponse,
                                ProjectConnectionTestRequest,
                                ProjectConnectionTestResponse,
                                ProjectCreateRequest, ProjectListResponse,
                                ProjectResponse, ProjectUpdateRequest)
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()


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

    # Encrypt database URLs at the API layer
    encrypted_postgres_url = encrypt_database_url(request.postgres_url) if request.postgres_url else ""
    encrypted_mongodb_url = encrypt_database_url(request.mongodb_url) if request.mongodb_url else ""

    # Create project
    project = await project_store.create_project_async(
        name=request.name,
        account_id=current_user.account_id,
        api_key=api_key,
        postgres_url=encrypted_postgres_url,
        mongodb_url=encrypted_mongodb_url,
        project_id=project_id,
    )

    # Return response with unmasked API key (only on creation)
    return ProjectResponse(
        id=project.id,
        name=project.name,
        account_id=project.account_id,
        api_key=project.api_key,  # Show full API key on creation
        postgres_url=mask_database_url(
            decrypt_database_url(project.postgres_url)),
        mongodb_url=mask_database_url(
            decrypt_database_url(project.mongodb_url)),
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

    return ProjectResponse(
        id=project.id,
        name=project.name,
        account_id=project.account_id,
        api_key="***",  # Mask API key on retrieval for security
        postgres_url=mask_database_url(
            decrypt_database_url(project.postgres_url)),
        mongodb_url=mask_database_url(
            decrypt_database_url(project.mongodb_url)),
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

    # Update project
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.postgres_url is not None:
        updates["postgres_url"] = encrypt_database_url(request.postgres_url)
    if request.mongodb_url is not None:
        updates["mongodb_url"] = encrypt_database_url(request.mongodb_url)

    updated_project = await project_store.update_project_async(project_id, **updates)

    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project",
        )

    return ProjectResponse(
        id=updated_project.id,
        name=updated_project.name,
        account_id=updated_project.account_id,
        api_key="***",  # Mask API key
        postgres_url=mask_database_url(
            decrypt_database_url(updated_project.postgres_url)
        ),
        mongodb_url=mask_database_url(
            decrypt_database_url(updated_project.mongodb_url)
        ),
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
    from app.core.db_test import (test_mongodb_connection,
                                  test_postgres_connection)

    project_store = get_project_store()
    postgres_url = request.postgres_url
    mongodb_url = request.mongodb_url

    # If project_id is provided, fetch the project and use its URLs
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

        # Verify project belongs to user's account
        if project.account_id != current_user.account_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this project",
            )

        # Decrypt and use project's URLs
        # Only decrypt if URL exists and is not empty or masked
        if project.postgres_url and project.postgres_url.strip() and not project.postgres_url.startswith("***"):
            try:
                postgres_url = decrypt_database_url(project.postgres_url)
            except Exception as e:
                # If decryption fails, log and skip
                import logging
                logging.warning(
                    f"Failed to decrypt postgres_url for project {project.id}: {e}")
                postgres_url = None
        if project.mongodb_url and project.mongodb_url.strip() and not project.mongodb_url.startswith("***"):
            try:
                mongodb_url = decrypt_database_url(project.mongodb_url)
            except Exception as e:
                # If decryption fails, log and skip
                import logging
                logging.warning(
                    f"Failed to decrypt mongodb_url for project {project.id}: {e}")
                mongodb_url = None

    results = ProjectConnectionTestResponse()

    # Test PostgreSQL if URL is available
    if postgres_url:
        pg_result = await test_postgres_connection(postgres_url)
        results.postgres = pg_result.to_dict()

    # Test MongoDB if URL is available
    if mongodb_url:
        mongo_result = await test_mongodb_connection(mongodb_url)
        results.mongodb = mongo_result.to_dict()

    if not postgres_url and not mongodb_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No database URLs available to test. Either provide project_id or postgres_url/mongodb_url",
        )

    return results
