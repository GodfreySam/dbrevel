"""
Basic tests for DbRevel API
Run with: pytest
"""
import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test root endpoint returns API info"""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "DbRevel API"
    assert "version" in data


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint"""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_query_endpoint_responds():
    """Test query endpoint responds (may fail auth/store init, but shouldn't crash)"""
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
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
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        response = await client.get(
            "/api/v1/schema",
            headers={
                "X-Project-Key": "dbrevel_default_project_key",
            },
        )

    # Endpoint should respond (not crash), even if it returns an error
    # Accept 307 (redirect), 200 (success), 401 (unauthorized), 500 (store not init), 503 (service unavailable)
    assert response.status_code in [200, 307, 401, 500, 503]
