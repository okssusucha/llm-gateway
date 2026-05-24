"""Per-key token-bucket rate limiter (in-memory)."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field


@dataclass
class _Bucket:
    tokens: float
    last: float = field(default_factory=time.monotonic)


class TokenBucketRateLimiter:
    """Allow ``capacity`` requests per key, refilling at ``refill_per_sec``."""

    def __init__(self, capacity: int, refill_per_sec: float) -> None:
        self._capacity = float(capacity)
        self._refill = float(refill_per_sec)
        self._buckets: dict[str, _Bucket] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(tokens=self._capacity, last=now)
                self._buckets[key] = bucket
            elapsed = now - bucket.last
            bucket.tokens = min(self._capacity, bucket.tokens + elapsed * self._refill)
            bucket.last = now
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True
            return False
