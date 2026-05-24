from fastapi.testclient import TestClient

from llm_gateway.app import create_app
from tests.conftest import API_KEY, make_settings


def test_rate_limit_429_after_burst():
    # capacity=3, no refill -> 4th request within the window must be rejected.
    settings = make_settings(rate_limit_capacity=3, rate_limit_refill_per_sec=0.0)
    client = TestClient(create_app(settings))
    headers = {"Authorization": f"Bearer {API_KEY}"}
    payload = {"model": "echo/x", "messages": [{"role": "user", "content": "hi"}]}

    statuses = [
        client.post("/v1/chat/completions", headers=headers, json=payload).status_code
        for _ in range(4)
    ]
    assert statuses[:3] == [200, 200, 200]
    assert statuses[3] == 429
