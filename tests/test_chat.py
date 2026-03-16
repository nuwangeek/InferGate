"""Tests for POST /v1/chat/completions and GET /v1/health.

How mocking works here:
- create_app() runs the lifespan, which stores a real VLLMClient on app.state.
- After the AsyncClient context starts (lifespan has run), we replace
  app.state.vllm_client with an AsyncMock.
- The get_vllm_client dependency reads from app.state on every request,
  so it picks up the mock without any monkey-patching of module globals.
"""

import time
import uuid
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.exceptions import VLLMError
from src.main import create_app
from src.models.chat import ChatCompletionResponse, Choice, Message, Usage


def _mock_response() -> ChatCompletionResponse:
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        object="chat.completion",
        created=int(time.time()),
        model="mock-model",
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content="Hello!"),
                finish_reason="stop",
            )
        ],
        usage=Usage(prompt_tokens=5, completion_tokens=5, total_tokens=10),
    )


@pytest.fixture
async def client_and_mock() -> AsyncIterator[tuple[AsyncClient, AsyncMock]]:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        mock_vllm = AsyncMock()
        app.state.vllm_client = mock_vllm
        yield ac, mock_vllm


async def test_chat_completion_success(
    client_and_mock: tuple[AsyncClient, AsyncMock],
) -> None:
    client, mock_vllm = client_and_mock
    mock_vllm.chat_completion.return_value = _mock_response()

    response = await client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["choices"][0]["message"]["content"] == "Hello!"
    assert data["usage"]["total_tokens"] == 10


async def test_chat_completion_vllm_unreachable(
    client_and_mock: tuple[AsyncClient, AsyncMock],
) -> None:
    client, mock_vllm = client_and_mock
    mock_vllm.chat_completion.side_effect = VLLMError(
        "Could not reach vLLM", status_code=503
    )

    response = await client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "vllm_error"
    assert "vLLM" in body["error"]["message"]


async def test_chat_completion_vllm_bad_response(
    client_and_mock: tuple[AsyncClient, AsyncMock],
) -> None:
    client, mock_vllm = client_and_mock
    mock_vllm.chat_completion.side_effect = VLLMError(
        "vLLM returned 500", status_code=502
    )

    response = await client.post(
        "/v1/chat/completions",
        json={
            "model": "mock-model",
            "messages": [{"role": "user", "content": "Hello"}],
        },
    )

    assert response.status_code == 502


async def test_chat_completion_missing_messages(
    client_and_mock: tuple[AsyncClient, AsyncMock],
) -> None:
    client, _ = client_and_mock

    response = await client.post(
        "/v1/chat/completions",
        json={"model": "mock-model"},  # messages required
    )

    assert response.status_code == 422  # FastAPI validation error


async def test_chat_completion_empty_messages(
    client_and_mock: tuple[AsyncClient, AsyncMock],
) -> None:
    client, _ = client_and_mock

    response = await client.post(
        "/v1/chat/completions",
        json={"model": "mock-model", "messages": []},  # min_length=1
    )

    assert response.status_code == 422


async def test_health_check(client: AsyncClient) -> None:
    response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
