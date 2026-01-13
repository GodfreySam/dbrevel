from fastapi import APIRouter, Depends
from app.adapters.factory import adapter_factory
from app.api.deps import get_security_context
from app.models.query import SecurityContext

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/")
async def get_all_schemas(
    security_ctx: SecurityContext = Depends(get_security_context)
):
    """
    Get schemas for all connected databases.
    Shows table/collection structures, relationships, and metadata.
    """
    schemas = adapter_factory.get_all_schemas()
    
    return {
        "databases": {
            name: schema.model_dump()
            for name, schema in schemas.items()
        }
    }


@router.get("/{database_name}")
async def get_database_schema(
    database_name: str,
    security_ctx: SecurityContext = Depends(get_security_context)
):
    """Get schema for a specific database"""
    try:
        adapter = adapter_factory.get(database_name)
        schema = adapter.get_schema()
        return schema.model_dump()
    except ValueError as e:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
