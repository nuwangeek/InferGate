from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Shallow health check — confirms the API process is alive.

    Later versions (v6) will add a /ready endpoint that also probes Redis,
    PostgreSQL, and vLLM before returning healthy.
    """
    return HealthResponse(status="ok")
