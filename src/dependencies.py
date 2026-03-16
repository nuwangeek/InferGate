from fastapi import Request

from src.services.vllm_client import VLLMClient


def get_vllm_client(request: Request) -> VLLMClient:
    """FastAPI dependency that pulls VLLMClient from app state.

    Why app.state instead of a module-level singleton: the lifespan manager owns
    the httpx.AsyncClient lifecycle (create on startup, close on shutdown).
    Storing it on app.state makes it easy to replace in tests without monkey-
    patching module globals.
    """
    return request.app.state.vllm_client  # type: ignore[no-any-return]
