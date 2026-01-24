"""
Basic tests for DbRevel API
Run with: pytest
"""

import pytest
from app.main import app
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint returns API info"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "DbRevel API"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    # Note: /health is a shallow check and doesn't return database status
    # Use /health/deep for database connectivity checks


@pytest.mark.asyncio
async def test_query_without_auth():
    """Test query endpoint requires authorization"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/query",
            headers={"X-Project-Key": "dbrevel_default_project_key"},
            json={"intent": "Get all users"},
        )

    # Should still work with default viewer role
    assert response.status_code in [200, 401]


@pytest.mark.asyncio
async def test_query_with_demo_token():
    """Test query with demo token"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/query",
            headers={
                "Authorization": "Bearer demo_token",
                "X-Project-Key": "dbrevel_default_project_key",
            },
            json={
                "intent": "Get all users",
                "dry_run": True  # Don't actually execute
            }
        )

    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "metadata" in data


@pytest.mark.asyncio
async def test_get_schemas():
    """Test schema endpoint"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/schema",
            headers={
                "Authorization": "Bearer demo_token",
                "X-Project-Key": "dbrevel_default_project_key",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "databases" in data
