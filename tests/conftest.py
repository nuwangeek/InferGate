from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """Basic async test client — no mocks wired in.

    Use this for endpoints that don't call vLLM (e.g. /health).
    For endpoints that do, use the client_and_mock fixture in test_chat.py.
    """
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
