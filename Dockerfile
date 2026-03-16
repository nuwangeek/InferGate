FROM python:3.12-slim

WORKDIR /app

# Copy uv binary from the official image — no need to install it via pip.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy lockfile and project metadata first.
# Docker layer caching: this layer only re-runs when dependencies change,
# not on every source code change — keeps rebuilds fast.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source last (changes most often).
COPY src/ ./src/

# Put the venv on PATH so we can call uvicorn directly.
ENV PATH="/app/.venv/bin:$PATH"

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
