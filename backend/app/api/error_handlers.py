"""Global exception handlers for the FastAPI application."""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.exceptions import (
    DbrevelError,
    QueryValidationError,
    InvalidQueryError,
    MissingCollectionError,
    UnsupportedQueryError,
    GeminiAPIError,
    GeminiResponseError,
    InvalidJSONError,
    InvalidQueryPlanError,
    MissingBYOApiKeyError,
)


async def dbrevel_error_handler(request: Request, exc: DbrevelError):
    """Base handler for application-specific errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


async def query_validation_error_handler(request: Request, exc: QueryValidationError):
    """Handler for query validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": f"Query Validation Failed: {exc}"},
    )


async def invalid_query_error_handler(request: Request, exc: InvalidQueryError):
    """Handler for invalid query errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"Invalid Query: {exc}"},
    )


async def missing_collection_error_handler(
    request: Request, exc: MissingCollectionError
):
    """Handler for missing collection errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"Missing Collection: {exc}"},
    )


async def unsupported_query_error_handler(request: Request, exc: UnsupportedQueryError):
    """Handler for unsupported query errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": f"Unsupported Query: {exc}"},
    )


async def gemini_api_error_handler(request: Request, exc: GeminiAPIError):
    """Handler for Gemini API errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Error communicating with AI model: {exc}"},
    )


async def gemini_response_error_handler(request: Request, exc: GeminiResponseError):
    """Handler for Gemini response errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Invalid response from AI model: {exc}"},
    )


async def invalid_json_error_handler(request: Request, exc: InvalidJSONError):
    """Handler for invalid JSON errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Could not parse response from AI model: {exc}"},
    )


async def invalid_query_plan_error_handler(
    request: Request, exc: InvalidQueryPlanError
):
    """Handler for invalid query plan errors."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Could not create query plan from AI response: {exc}"},
    )


async def missing_byo_api_key_error_handler(
    request: Request, exc: MissingBYOApiKeyError
):
    """Handler for missing BYO API key errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


def add_exception_handlers(app):
    """Add all custom exception handlers to the FastAPI app."""
    app.add_exception_handler(DbrevelError, dbrevel_error_handler)
    app.add_exception_handler(QueryValidationError, query_validation_error_handler)
    app.add_exception_handler(InvalidQueryError, invalid_query_error_handler)
    app.add_exception_handler(MissingCollectionError, missing_collection_error_handler)
    app.add_exception_handler(UnsupportedQueryError, unsupported_query_error_handler)
    app.add_exception_handler(GeminiAPIError, gemini_api_error_handler)
    app.add_exception_handler(GeminiResponseError, gemini_response_error_handler)
    app.add_exception_handler(InvalidJSONError, invalid_json_error_handler)
    app.add_exception_handler(InvalidQueryPlanError, invalid_query_plan_error_handler)
    app.add_exception_handler(MissingBYOApiKeyError, missing_byo_api_key_error_handler)
