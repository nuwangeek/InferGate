import httpx

from src.exceptions import VLLMError
from src.models.chat import ChatCompletionRequest, ChatCompletionResponse


class VLLMClient:
    """HTTP client for the vLLM inference service.

    Why a class instead of bare functions: it holds two pieces of shared state —
    the httpx.AsyncClient (connection pool) and the configured model name.
    Both are expensive to create per-request; the class keeps them alive for the
    app's lifetime and lets tests swap the whole client out easily.
    """

    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        model: str,
    ) -> None:
        self._client = http_client
        self._base_url = base_url
        self._model = model

    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:
        """Forward a chat completion request to vLLM and return the parsed response."""
        payload = request.model_dump(exclude_none=True)
        payload["model"] = self._model  # always use the server-configured model

        try:
            response = await self._client.post(
                f"{self._base_url}/v1/chat/completions",
                json=payload,
                timeout=60.0,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise VLLMError(
                message=f"vLLM returned {exc.response.status_code}",
                status_code=502,
            ) from exc
        except httpx.RequestError as exc:
            # Covers connection refused, DNS failure, timeouts, etc.
            raise VLLMError(
                message=f"Could not reach vLLM: {exc}",
                status_code=503,
            ) from exc

        return ChatCompletionResponse.model_validate(response.json())
