"""Shared test fixtures. Everything runs offline with the echo provider."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from llm_gateway.app import create_app
from llm_gateway.config import Settings

API_KEY = "test-key"


def make_settings(**overrides) -> Settings:
    base = dict(
        api_keys=API_KEY,
        default_provider="echo",
        cache_enabled=True,
        cache_ttl_seconds=300,
        rate_limit_capacity=1000,
        rate_limit_refill_per_sec=1000.0,
        redis_url=None,
        openai_api_key=None,
        anthropic_api_key=None,
    )
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app(make_settings()))


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {API_KEY}"}
