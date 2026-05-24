"""Response caching.

In-memory TTL cache by default; a Redis-backed cache is used when ``REDIS_URL``
is configured and the redis client is installed. Both implement the same small
interface so the rest of the app is agnostic.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Protocol

from llm_gateway.schemas import ChatCompletionRequest


class Cache(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str) -> None: ...


def cache_key(request: ChatCompletionRequest) -> str:
    """Stable key over the routing-relevant fields of a request."""
    payload = {
        "model": request.model,
        "messages": [m.model_dump() for m in request.messages],
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()


class InMemoryCache:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, tuple[float, str]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        now = time.monotonic()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires, value = entry
            if expires < now:
                self._store.pop(key, None)
                return None
            return value

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._store[key] = (time.monotonic() + self._ttl, value)


class RedisCache:
    def __init__(self, url: str, ttl_seconds: int) -> None:
        import redis  # imported lazily so redis stays optional

        self._client = redis.Redis.from_url(url)
        self._ttl = ttl_seconds

    def get(self, key: str) -> str | None:
        value = self._client.get(key)
        return value.decode() if isinstance(value, bytes) else value

    def set(self, key: str, value: str) -> None:
        self._client.set(key, value, ex=self._ttl)


def build_cache(redis_url: str | None, ttl_seconds: int) -> Cache:
    if redis_url:
        try:
            return RedisCache(redis_url, ttl_seconds)
        except Exception:  # noqa: BLE001 - fall back gracefully if redis unavailable
            return InMemoryCache(ttl_seconds)
    return InMemoryCache(ttl_seconds)
