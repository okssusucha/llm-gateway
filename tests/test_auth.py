def _payload():
    return {"model": "echo/test", "messages": [{"role": "user", "content": "hi"}]}


def test_missing_auth_header(client):
    resp = client.post("/v1/chat/completions", json=_payload())
    assert resp.status_code == 401


def test_invalid_key(client):
    resp = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer wrong-key"},
        json=_payload(),
    )
    assert resp.status_code == 401


def test_valid_key(client, auth_headers):
    resp = client.post("/v1/chat/completions", headers=auth_headers, json=_payload())
    assert resp.status_code == 200
