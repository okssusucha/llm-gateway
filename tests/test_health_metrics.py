def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["default_provider"] == "echo"
    assert "echo" in body["providers"]


def test_metrics_prometheus_format(client, auth_headers):
    client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "echo/test", "messages": [{"role": "user", "content": "hi"}]},
    )
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "gateway_requests_total" in resp.text
    assert 'gateway_requests_total{provider="echo"}' in resp.text
    assert "gateway_request_latency_seconds_count" in resp.text
