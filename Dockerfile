# syntax=docker/dockerfile:1
FROM python:3.12-slim

# Install uv (the project's package manager).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    GATEWAY_HOST=0.0.0.0 \
    GATEWAY_PORT=8080

WORKDIR /app

# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY src ./src
RUN uv sync --no-dev

EXPOSE 8080

# Runs with the default echo provider unless provider keys are supplied via env.
CMD ["uv", "run", "uvicorn", "llm_gateway.app:app", "--host", "0.0.0.0", "--port", "8080"]
