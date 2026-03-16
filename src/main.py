from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.config import Settings
from src.exceptions import VLLMError
from src.routers import chat, health
from src.services.vllm_client import VLLMClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """App startup and shutdown logic.

    Why lifespan instead of @app.on_event: lifespan is the modern FastAPI
    approach and makes it obvious that everything before `yield` is startup
    and everything after is shutdown.

    The single httpx.AsyncClient is created here and shared across all requests
    via app.state. One client = one connection pool = far fewer TCP handshakes
    under load compared to creating a new client per request.
    """
    settings = Settings()
    http_client = httpx.AsyncClient()

    app.state.settings = settings
    app.state.http_client = http_client
    app.state.vllm_client = VLLMClient(
        http_client=http_client,
        base_url=settings.vllm_base_url,
        model=settings.vllm_model,
    )

    yield  # app serves requests here

    await http_client.aclose()  # graceful shutdown: drain in-flight requests


def create_app() -> FastAPI:
    """App factory — returns a configured FastAPI instance.

    Why a factory instead of a module-level `app = FastAPI()`: tests can call
    create_app() to get a fresh app instance each time, avoiding state leaking
    between test cases.
    """
    app = FastAPI(title="InferGate", version="0.0.1", lifespan=lifespan)

    app.include_router(chat.router, prefix="/v1")
    app.include_router(health.router, prefix="/v1")

    @app.exception_handler(VLLMError)
    async def vllm_error_handler(request: Request, exc: VLLMError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "vllm_error", "message": exc.message}},
        )

    return app


# Module-level app instance required by uvicorn (src.main:app).
app = create_app()
