from app.adapters.factory import adapter_factory
from app.api.deps import get_security_context
from app.core.accounts import AccountConfig, get_account_config
from app.core.demo_account import get_demo_account_config
from app.models.query import SecurityContext
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get(
    "/",
    summary="Get All Database Schemas",
    description="""
Get schemas for all connected databases in your project.

This endpoint returns the complete database schema including:
- **PostgreSQL**: Tables, columns, data types, constraints, relationships
- **MongoDB**: Collections, fields, indexes, document structure

**Use cases:**
- Understand your database structure before writing queries
- Discover available tables/collections and their fields
- Plan natural language queries based on schema

**Authentication:**
- Use `X-Project-Key` header with your project API key
- Or leave empty to use demo project with sample data
    """,
    responses={
        200: {
            "description": "Schemas retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "databases": {
                            "postgres": {
                                "name": "postgres",
                                "type": "postgresql",
                                "tables": [
                                    {
                                        "name": "users",
                                        "columns": [
                                            {
                                                "name": "id",
                                                "type": "integer",
                                                "nullable": False,
                                            },
                                            {
                                                "name": "email",
                                                "type": "varchar",
                                                "nullable": False,
                                            },
                                            {
                                                "name": "name",
                                                "type": "varchar",
                                                "nullable": True,
                                            },
                                        ],
                                    }
                                ],
                            },
                            "mongodb": {
                                "name": "mongodb",
                                "type": "mongodb",
                                "collections": [
                                    {
                                        "name": "reviews",
                                        "fields": [
                                            "_id",
                                            "user_id",
                                            "product_id",
                                            "rating",
                                            "comment",
                                        ],
                                    }
                                ],
                            },
                        }
                    }
                }
            },
        }
    },
)
async def get_all_schemas(
    security_ctx: SecurityContext = Depends(get_security_context),
    tenant: AccountConfig = Depends(get_account_config),
):
    """
    Get schemas for all connected databases.
    Shows table/collection structures, relationships, and metadata.
    """
    # If no tenant provided, use demo account
    if not tenant:
        tenant = get_demo_account_config()

    schemas = await adapter_factory.get_all_schemas(tenant)

    return {
        "databases": {name: schema.model_dump() for name, schema in schemas.items()}
    }


@router.get(
    "/{database_name}",
    summary="Get Database Schema",
    description="""
Get schema for a specific database (PostgreSQL or MongoDB).

**Parameters:**
- `database_name`: Name of the database (e.g., "postgres", "mongodb")

**Returns:**
- Complete schema for the specified database
- Tables/collections with all fields and metadata

**Example:**
- `/api/v1/schema/postgres` - Get PostgreSQL schema
- `/api/v1/schema/mongodb` - Get MongoDB schema
    """,
    responses={
        200: {"description": "Schema retrieved successfully"},
        404: {
            "description": "Database not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Database 'invalid_db' not found"}
                }
            },
        },
    },
)
async def get_database_schema(
    database_name: str,
    security_ctx: SecurityContext = Depends(get_security_context),
    tenant: AccountConfig = Depends(get_account_config),
):
    """Get schema for a specific database"""
    # If no tenant provided, use demo account
    if not tenant:
        tenant = get_demo_account_config()

    try:
        adapter = await adapter_factory.get(tenant, database_name)
        schema = await adapter.introspect_schema()
        return schema.model_dump()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
