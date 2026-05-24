def test_cache_hit_returns_same_response_and_increments_metric(client, auth_headers):
    payload = {"model": "echo/cache", "messages": [{"role": "user", "content": "cache me"}]}

    first = client.post("/v1/chat/completions", headers=auth_headers, json=payload)
    second = client.post("/v1/chat/completions", headers=auth_headers, json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    # Cached response is byte-identical, including the generated id.
    assert first.json()["id"] == second.json()["id"]

    metrics = client.get("/metrics").text
    assert "gateway_cache_hits_total 1" in metrics
    assert "gateway_cache_misses_total 1" in metrics
