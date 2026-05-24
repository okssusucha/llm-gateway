"""Routing + real-provider tests. All upstream HTTP is mocked with respx, so
these run fully offline with no keys and no network access."""

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from llm_gateway.app import create_app
from llm_gateway.router import ProviderRouter
from tests.conftest import API_KEY, make_settings


def test_router_resolves_by_prefix():
    router = ProviderRouter(make_settings(openai_api_key="sk-test", anthropic_api_key="ak-test"))
    assert router.resolve("openai/gpt-4o").name == "openai"
    assert router.resolve("anthropic/claude-3").name == "anthropic"
    assert router.resolve("echo/x").name == "echo"
    # Bare names map by family.
    assert router.resolve("gpt-4o").name == "openai"
    assert router.resolve("claude-3-5-sonnet").name == "anthropic"


def test_router_falls_back_to_echo_without_key():
    router = ProviderRouter(make_settings())  # no keys
    assert router.resolve("gpt-4o").name == "echo"
    assert router.resolve("openai/gpt-4o").name == "echo"


@respx.mock
def test_openai_provider_mocked_http():
    settings = make_settings(
        openai_api_key="sk-test",
        openai_base_url="https://api.openai.com/v1",
        cache_enabled=False,
    )
    route = respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200,
            json={
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": 1,
                "model": "gpt-4o",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "mocked reply"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            },
        )
    )
    client = TestClient(create_app(settings))
    resp = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": "openai/gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 200
    assert route.called
    assert resp.json()["choices"][0]["message"]["content"] == "mocked reply"


@respx.mock
def test_anthropic_provider_mocked_http():
    settings = make_settings(
        anthropic_api_key="ak-test",
        anthropic_base_url="https://api.anthropic.com/v1",
        cache_enabled=False,
    )
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={
                "model": "claude-3-5-sonnet",
                "content": [{"type": "text", "text": "claude reply"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 5, "output_tokens": 7},
            },
        )
    )
    client = TestClient(create_app(settings))
    resp = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={
            "model": "anthropic/claude-3-5-sonnet",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert resp.status_code == 200
    assert route.called
    body = resp.json()
    assert body["choices"][0]["message"]["content"] == "claude reply"
    assert body["usage"]["total_tokens"] == 12


@respx.mock
def test_provider_http_error_returns_502():
    settings = make_settings(
        openai_api_key="sk-test",
        openai_base_url="https://api.openai.com/v1",
        cache_enabled=False,
    )
    respx.post("https://api.openai.com/v1/chat/completions").mock(
        return_value=httpx.Response(500, json={"error": "boom"})
    )
    client = TestClient(create_app(settings))
    resp = client.post(
        "/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": "openai/gpt-4o", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert resp.status_code == 502


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__])
