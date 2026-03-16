# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InferGate is a production-grade chat API gateway backed by vLLM for inference. Built incrementally across 8 versions (v0–v7), each adding one scalability concern. The AI part is intentionally simple — the API layer is the focus. This is an interview preparation project for an Associate Tech Lead – AI Engineering role.

Each version must be a fully working, runnable API. Use git tags (`v0`, `v1`, ...) to mark milestones.

| Version | Focus | Key Addition |
|---------|-------|-------------|
| v0 | Foundation | FastAPI + vLLM proxy, Pydantic models, Docker |
| v1 | Streaming | SSE token-by-token streaming |
| v2 | Auth & Security | API key auth, PostgreSQL, Nginx, input guardrails |
| v3 | Rate Limiting | Redis sliding window, Lua scripts, tiered limits |
| v4 | Backpressure | Semaphore, bounded queue, circuit breaker |
| v5 | Caching | Redis exact-match cache, TTL, cache headers |
| v6 | Observability | Prometheus, Grafana, Loki, structlog, health checks |
| v7 | Scaling Proof | Multi-replica, load testing with Locust/k6, reports |

## Build & Run Commands

```bash
# First-time setup
cp .env.example .env                 # then edit VLLM_BASE_URL / VLLM_MODEL as needed

# Package manager: uv (not pip)
uv sync                              # Install dependencies
uv run pytest                        # Run all tests
uv run pytest tests/test_chat.py     # Run single test file
uv run pytest -k "test_name"         # Run single test by name
uv run pytest -x                     # Stop on first failure

# Docker
docker compose up --build            # Build and run all services
docker compose up -d                 # Run detached
docker compose down                  # Stop all services

# Local dev server (without Docker)
# src/main.py must expose `app = create_app()` at module level
uv run uvicorn src.main:app --reload --port 8000

# DB migrations (from v2)
uv run alembic upgrade head          # Apply migrations
uv run alembic revision --autogenerate -m "description"  # Create migration

# Linting & formatting (ruff configured in pyproject.toml)
uv run ruff check src/ tests/        # Lint
uv run ruff format src/ tests/       # Format
uv run ruff check --fix src/         # Auto-fix lint issues

# Git workflow
git tag v0                           # Tag version milestones
# Commit format: "v{N}: brief description"
```

## Architecture

**Request flow**: Client → Nginx (v2+) → FastAPI → Service layer → vLLM (OpenAI-compatible `/v1/chat/completions`)

**Key patterns**:
- **App factory**: `create_app()` in `src/main.py` with lifespan context manager for `httpx.AsyncClient` lifecycle
- **Dependency injection**: All services (auth, rate limiter, cache, etc.) injected via FastAPI `Depends()` — never imported directly in route handlers
- **Service layer**: Route handlers delegate to `src/services/` — no business logic in routes
- **Config**: `pydantic-settings` `BaseSettings` in `src/config.py`, all values from environment variables
- **Custom exceptions**: Defined in `src/exceptions.py`, handled by app-level exception handlers (not try/except in routes)
- **Error format**: `{"error": {"code": "rate_limit_exceeded", "message": "...", "retry_after": 30}}`

**API design**: Follows OpenAI API schema. All endpoints prefixed with `/v1/`. The same `/v1/chat/completions` endpoint handles both streaming and non-streaming via `stream: bool` field.

## Tech Stack

- Python 3.12+, FastAPI, Pydantic v2, `httpx.AsyncClient` (connection-pooled, never `requests`)
- PostgreSQL via `asyncpg` + SQLAlchemy 2.0 async (v2+), Redis via `redis.asyncio` (v3+)
- vLLM with OpenAI-compatible API, Nginx as reverse proxy/LB
- Docker + Docker Compose, `uv` package manager
- Testing: `pytest` + `pytest-asyncio`, `httpx.AsyncClient` with `ASGITransport`
- Linting/formatting: `ruff` | Type checking: `pyright` (both configured in `pyproject.toml`)

## Critical Coding Rules

- **Async everywhere**: No `requests`, `psycopg2`, `redis.Redis` (sync), or `time.sleep()`. Use async equivalents.
- **No `Any` type**: Type all dict keys/values explicitly. Type hints on all function args and return types.
- **Pydantic v2 syntax**: `model_config = ConfigDict(...)`, `Field()` with descriptions, `Annotated` types, strict constraints (`max_length`, `ge`, `le`).
- **Single `httpx.AsyncClient`**: Created on app startup, closed on shutdown via lifespan. Never create per-request.
- **Docker networking**: Use service names, not `localhost`.
- **Streaming**: SSE format `data: {json}\n\n`, final chunk `data: [DONE]\n\n`, handle `asyncio.CancelledError` for disconnects.

## Naming Conventions

- Files: `snake_case.py` | Classes: `PascalCase` | Functions/vars: `snake_case` | Constants: `UPPER_SNAKE_CASE`
- Pydantic models: suffixed — `ChatCompletionRequest`, `ChatCompletionResponse`, `APIKeyCreate`
- Router files: named by resource — `chat.py`, `admin.py`, `health.py`

## Testing

- Use `httpx.AsyncClient` with `ASGITransport`, not `TestClient`
- Mock vLLM responses — tests must not depend on running vLLM
- `pytest-asyncio` runs in `auto` mode — no `@pytest.mark.asyncio` decorator needed
- `tests/conftest.py` provides a bare `client` fixture (no vLLM mock) for endpoints like `/health`; tests that call vLLM routes define their own mock fixture (e.g. `client_and_mock` in `test_chat.py`) by overriding `app.state.vllm_client`
- Test both happy paths and error cases (bad auth, rate limited, vLLM down)

## Version-Specific Notes

**v0**: Factory pattern app, lifespan-managed `httpx.AsyncClient`, `VLLMClient` class with `chat_completion()` method. Docker Compose: `api` + `vllm` services. `mock_vllm/` is a self-contained FastAPI app with its own `Dockerfile` and `requirements.txt`; it is the `vllm` service in `docker-compose.yml` so the full stack runs without a GPU. Its response shape is identical to real vLLM.

**v1**: `StreamingResponse(media_type="text/event-stream")` with async generator. Same endpoint handles stream/non-stream.

**v2**: API keys via `secrets.token_urlsafe(32)`, SHA-256 hashed in PostgreSQL. Auth as FastAPI dependency. Alembic for migrations. Nginx with `client_max_body_size 1m`. Security headers middleware. Restrictive CORS.

**v3**: Sliding window counter via Redis sorted sets + Lua script (ZADD + ZREMRANGEBYSCORE + ZCARD atomic). Two limits: RPM and TPD. Tiers stored in API keys table. Rate limiter is a dependency, not middleware.

**v4**: `asyncio.Semaphore` (default 20 concurrent), `asyncio.wait_for()` with timeout. Circuit breaker on vLLM client. 503 when circuit open, 429 when queue full.

**v5**: Cache key = SHA-256 of canonical JSON (model, messages, temperature, max_tokens). Only cache `temperature == 0`. Redis with configurable TTL (default 5 min). `X-Cache: HIT/MISS` header. Don't cache streaming.

**v6**: `prometheus_client` on `/metrics`. Metrics: `http_requests_total`, `http_request_duration_seconds`, `vllm_inflight_requests`, `tokens_generated_total`, `cache_hits/misses_total`, `rate_limit_rejections_total`. `structlog` JSON output. `/v1/health` (shallow) and `/v1/ready` (deep: Redis + PG + vLLM).

**v7**: 3 API replicas, Nginx `least_conn`. Tune `asyncpg` pool (min=5, max=20/replica). Locust scenarios. HTML reports in `load-tests/reports/`. Write `SCALABILITY.md`.
