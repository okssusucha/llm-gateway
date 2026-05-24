# llm-gateway

Provider-agnostic **LLM API gateway**: a single OpenAI-compatible endpoint that
routes to multiple backends (OpenAI, Anthropic, and a built-in offline `echo`
provider) with API-key auth, per-key rate limiting, response caching, and
Prometheus metrics.

プロバイダ非依存の **LLM API ゲートウェイ**。OpenAI 互換のエンドポイントを1つ
公開し、複数のバックエンド（OpenAI / Anthropic / オフライン用の `echo`
プロバイダ）へルーティングします。APIキー認証・キー単位のレート制限・
レスポンスキャッシュ・Prometheus メトリクスを備えています。

---

## Why a gateway? / なぜゲートウェイか

**EN**

- **Cost control** — one place to enforce per-key rate limits and cache
  identical requests, so you don't pay an upstream provider twice for the same
  prompt.
- **Multi-provider** — clients speak one OpenAI-compatible API; switching or
  mixing providers (OpenAI, Anthropic, local) is a routing decision, not a
  client rewrite.
- **Observability** — centralized structured logs and `/metrics` give you
  request counts, latency, cache hit rate, and rate-limit rejections across all
  providers in one place.

**JA**

- **コスト管理** — レート制限とキャッシュを1か所で適用。同じプロンプトに対して
  上流プロバイダへ二重課金されるのを防ぎます。
- **マルチプロバイダ** — クライアントは OpenAI 互換 API だけを話せばよく、
  プロバイダの切り替え・併用はルーティング設定だけで完結します。
- **可観測性** — 構造化ログと `/metrics` を集約し、リクエスト数・レイテンシ・
  キャッシュヒット率・レート制限拒否を横断的に把握できます。

---

## Architecture / アーキテクチャ

```
                 ┌─────────────────────────────────────────────┐
   client  ──▶   │  FastAPI gateway                            │
 (OpenAI SDK)    │                                             │
                 │  auth ─▶ rate limit ─▶ cache ─▶ router      │
                 │   │         │            │         │         │
                 │  keys   token bucket   mem/Redis   │         │
                 │                                     ▼         │
                 │                          ┌──────────────────┐│
                 │                          │ Provider adapters ││
                 │                          │  • echo (default)││
                 │                          │  • openai        ││
                 │                          │  • anthropic     ││
                 │                          └──────────────────┘│
                 │  structured logs + /metrics (Prometheus)     │
                 └─────────────────────────────────────────────┘
```

Routing picks a provider from the model name: a prefix like `openai/`,
`anthropic/`, or `echo/`; otherwise `gpt-*`/`o1`/`o3` → OpenAI, `claude*` →
Anthropic. **If the matched provider has no API key configured, the request
falls back to the `echo` provider** — so the gateway always works offline.

---

## Quickstart / クイックスタート

### With uv (local) / uv で起動

```bash
uv sync
uv run uvicorn llm_gateway.app:app --host 0.0.0.0 --port 8080
# or: uv run llm-gateway
```

### With Docker / Docker で起動

```bash
docker compose up --build
# gateway -> http://localhost:8080  (redis bundled)
```

No keys required — the gateway boots on the deterministic `echo` provider.
キー不要。`echo` プロバイダで起動します。

---

## curl examples / curl 例

Default key is `demo-key`. The `echo` provider echoes your last user message.

```bash
# Health
curl -s http://localhost:8080/health | jq

# Chat completion via the offline echo provider
curl -s http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer demo-key" \
  -H "Content-Type: application/json" \
  -d '{
        "model": "echo/demo",
        "messages": [{"role": "user", "content": "hello world"}]
      }' | jq
# -> choices[0].message.content == "echo: hello world"

# Metrics (Prometheus text format)
curl -s http://localhost:8080/metrics
```

Once real keys are set, point clients at a routed model name:

```bash
curl -s http://localhost:8080/v1/chat/completions \
  -H "Authorization: Bearer demo-key" \
  -d '{"model": "openai/gpt-4o", "messages": [{"role":"user","content":"hi"}]}'
```

---

## Configuration / 設定

All settings use the `GATEWAY_` env prefix (see `.env.example`).

| Env var | Default | Meaning |
|---|---|---|
| `GATEWAY_API_KEYS` | `demo-key` | Comma-separated gateway-issued client keys |
| `GATEWAY_DEFAULT_PROVIDER` | `echo` | Fallback provider (keeps gateway offline-capable) |
| `GATEWAY_OPENAI_API_KEY` | _unset_ | Enables the OpenAI backend |
| `GATEWAY_OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI base URL |
| `GATEWAY_ANTHROPIC_API_KEY` | _unset_ | Enables the Anthropic backend |
| `GATEWAY_ANTHROPIC_BASE_URL` | `https://api.anthropic.com/v1` | Anthropic base URL |
| `GATEWAY_RATE_LIMIT_CAPACITY` | `60` | Token-bucket capacity per key |
| `GATEWAY_RATE_LIMIT_REFILL_PER_SEC` | `1.0` | Bucket refill rate (tokens/sec) |
| `GATEWAY_CACHE_ENABLED` | `true` | Toggle response caching |
| `GATEWAY_CACHE_TTL_SECONDS` | `300` | Cache TTL |
| `GATEWAY_REDIS_URL` | _unset_ | Use Redis cache; falls back to in-memory if absent |

---

## Metrics / メトリクス

`GET /metrics` returns Prometheus text format:

- `gateway_requests_total{provider="..."}` — requests per provider
- `gateway_errors_total` — upstream/provider errors
- `gateway_cache_hits_total` / `gateway_cache_misses_total`
- `gateway_rate_limited_total` — requests rejected with HTTP 429
- `gateway_request_latency_seconds_sum` / `_count` — latency aggregate

---

## Development / 開発

```bash
uv sync
uv run ruff check .     # lint
uv run pytest           # tests run fully offline; upstream HTTP is mocked (respx)
```

CI (`.github/workflows/ci.yml`) runs ruff + pytest on Python 3.11 and 3.12 with
**no secrets** — every test uses the echo provider or mocked HTTP.

---

## License / ライセンス

MIT. See [LICENSE](LICENSE).
