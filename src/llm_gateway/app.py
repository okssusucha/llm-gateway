"""FastAPI application wiring auth, routing, rate limiting, caching, metrics."""

from __future__ import annotations

import time

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, PlainTextResponse

from llm_gateway import __version__
from llm_gateway.cache import build_cache, cache_key
from llm_gateway.config import Settings, get_settings
from llm_gateway.logging_config import configure_logging, log_event
from llm_gateway.metrics import Metrics
from llm_gateway.ratelimit import TokenBucketRateLimiter
from llm_gateway.router import ProviderRouter
from llm_gateway.schemas import ChatCompletionRequest, ChatCompletionResponse


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logger = configure_logging()

    app = FastAPI(title="llm-gateway", version=__version__)
    app.state.settings = settings
    app.state.router = ProviderRouter(settings)
    app.state.metrics = Metrics()
    app.state.rate_limiter = TokenBucketRateLimiter(
        settings.rate_limit_capacity, settings.rate_limit_refill_per_sec
    )
    app.state.cache = (
        build_cache(settings.redis_url, settings.cache_ttl_seconds)
        if settings.cache_enabled
        else None
    )

    def authenticate(authorization: str | None = Header(default=None)) -> str:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or malformed Authorization header (expected: Bearer <key>).",
            )
        key = authorization.split(" ", 1)[1].strip()
        if key not in settings.parsed_api_keys():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key."
            )
        return key

    @app.get("/health")
    async def health() -> dict:
        return {
            "status": "ok",
            "version": __version__,
            "default_provider": settings.default_provider,
            "providers": app.state.router.available(),
        }

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics() -> str:
        return app.state.metrics.render()

    @app.post("/v1/chat/completions")
    async def chat_completions(
        request: ChatCompletionRequest,
        api_key: str = Depends(authenticate),
    ) -> ChatCompletionResponse:
        metrics_obj: Metrics = app.state.metrics
        limiter: TokenBucketRateLimiter = app.state.rate_limiter
        if not limiter.allow(api_key):
            metrics_obj.record_rate_limited()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded.",
            )

        cache = app.state.cache
        key = cache_key(request) if cache is not None else None
        if cache is not None and key is not None:
            cached = cache.get(key)
            if cached is not None:
                metrics_obj.record_cache(hit=True)
                log_event(logger, "cache_hit", model=request.model)
                cached_response = ChatCompletionResponse.model_validate_json(cached)
                return JSONResponse(content=cached_response.model_dump())
            metrics_obj.record_cache(hit=False)

        provider = app.state.router.resolve(request.model)
        started = time.monotonic()
        try:
            response = await provider.chat_completion(request)
        except httpx.HTTPError as exc:
            metrics_obj.record_error()
            log_event(logger, "provider_error", provider=provider.name, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Upstream provider error: {exc}",
            ) from exc

        latency = time.monotonic() - started
        metrics_obj.record_request(provider.name, latency)
        log_event(
            logger,
            "chat_completion",
            provider=provider.name,
            model=request.model,
            latency_ms=round(latency * 1000, 2),
        )

        if cache is not None and key is not None:
            cache.set(key, response.model_dump_json())
        return response

    @app.exception_handler(Exception)
    async def unhandled(_: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
        app.state.metrics.record_error()
        return JSONResponse(status_code=500, content={"detail": "Internal server error."})

    return app


app = create_app()
