def test_echo_chat_completion(client, auth_headers):
    resp = client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={
            "model": "echo/demo",
            "messages": [
                {"role": "system", "content": "be brief"},
                {"role": "user", "content": "hello world"},
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["object"] == "chat.completion"
    assert body["model"] == "echo/demo"
    assert body["choices"][0]["message"]["content"] == "echo: hello world"
    assert body["choices"][0]["message"]["role"] == "assistant"
    assert body["usage"]["total_tokens"] > 0


def test_unknown_model_falls_back_to_echo(client, auth_headers):
    # No real keys configured -> any model routes to the default echo provider.
    resp = client.post(
        "/v1/chat/completions",
        headers=auth_headers,
        json={"model": "gpt-4o", "messages": [{"role": "user", "content": "ping"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "echo: ping"
