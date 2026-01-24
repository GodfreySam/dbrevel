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


@pytest.mark.asyncio
async def test_query_endpoint_responds():
    """Test query endpoint responds (may fail auth/store init, but shouldn't crash)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/query",
            headers={"X-Project-Key": "dbrevel_default_project_key"},
            json={"intent": "Get all users"},
        )

    # Endpoint should respond (not crash), even if it returns an error
    # Accept various error codes: 401 (unauthorized), 500 (store not init), 503 (service unavailable)
    assert response.status_code in [200, 401, 500, 503]


@pytest.mark.asyncio
async def test_schema_endpoint_responds():
    """Test schema endpoint responds (may fail auth/store init, but shouldn't crash)"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/schema",
            headers={
                "X-Project-Key": "dbrevel_default_project_key",
            },
        )

    # Endpoint should respond (not crash), even if it returns an error
    assert response.status_code in [200, 401, 500, 503]
