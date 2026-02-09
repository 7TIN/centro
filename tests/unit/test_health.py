import os

import pytest
from httpx import AsyncClient


# Ensure required settings are present before importing the app
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("POSTGRES_USER", "test")
os.environ.setdefault("POSTGRES_PASSWORD", "test")
os.environ.setdefault("POSTGRES_DB", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-chars")

from src.main import app  # noqa: E402


@pytest.mark.asyncio
async def test_root_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["health"] == "/health"
    assert data["docs"] == "/docs"


@pytest.mark.asyncio
async def test_health_endpoint(monkeypatch):
    async def fake_check_db_connection() -> bool:
        return True

    monkeypatch.setattr("src.main.check_db_connection", fake_check_db_connection)

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] is True
    assert "timestamp" in data
