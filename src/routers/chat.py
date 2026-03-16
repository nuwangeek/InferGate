from fastapi import APIRouter, Depends

from src.dependencies import get_vllm_client
from src.models.chat import ChatCompletionRequest, ChatCompletionResponse
from src.services.vllm_client import VLLMClient

router = APIRouter()


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(
    body: ChatCompletionRequest,
    vllm_client: VLLMClient = Depends(get_vllm_client),
) -> ChatCompletionResponse:
    """Proxy a chat completion request to vLLM.

    The route handler itself has zero business logic — it just binds the HTTP
    layer (FastAPI) to the service layer (VLLMClient). All error handling lives
    in the app-level exception handler registered in main.py.
    """
    return await vllm_client.chat_completion(body)
