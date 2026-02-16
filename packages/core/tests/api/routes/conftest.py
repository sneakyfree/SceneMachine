"""Shared fixtures for API route tests.

Provides a reusable `app` fixture and an `async_client` fixture so that
individual route test files don't need to duplicate setup code.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from scenemachine.api.app import create_app


@pytest.fixture(scope="module")
def app():
    """Create a test FastAPI application instance.

    Scoped to module so that the app is created once per test file,
    reducing overhead while keeping tests isolated between files.
    """
    return create_app()


@pytest_asyncio.fixture
async def async_client(app):
    """Create an async HTTP client wired to the test app.

    Usage in tests:
        async def test_something(async_client):
            response = await async_client.get("/api/v1/some/endpoint")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
