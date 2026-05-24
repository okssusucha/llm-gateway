"""Minimal Prometheus-style metrics (no external client dependency)."""

from __future__ import annotations

import threading


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.requests_total: dict[str, int] = {}
        self.errors_total = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.rate_limited_total = 0
        self._latency_sum = 0.0
        self._latency_count = 0

    def record_request(self, provider: str, latency_s: float) -> None:
        with self._lock:
            self.requests_total[provider] = self.requests_total.get(provider, 0) + 1
            self._latency_sum += latency_s
            self._latency_count += 1

    def record_error(self) -> None:
        with self._lock:
            self.errors_total += 1

    def record_cache(self, hit: bool) -> None:
        with self._lock:
            if hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1

    def record_rate_limited(self) -> None:
        with self._lock:
            self.rate_limited_total += 1

    def render(self) -> str:
        with self._lock:
            lines = [
                "# HELP gateway_requests_total Total chat completion requests by provider.",
                "# TYPE gateway_requests_total counter",
            ]
            for provider, count in sorted(self.requests_total.items()):
                lines.append(f'gateway_requests_total{{provider="{provider}"}} {count}')
            lines += [
                "# HELP gateway_errors_total Total upstream/provider errors.",
                "# TYPE gateway_errors_total counter",
                f"gateway_errors_total {self.errors_total}",
                "# HELP gateway_cache_hits_total Cache hits.",
                "# TYPE gateway_cache_hits_total counter",
                f"gateway_cache_hits_total {self.cache_hits}",
                "# HELP gateway_cache_misses_total Cache misses.",
                "# TYPE gateway_cache_misses_total counter",
                f"gateway_cache_misses_total {self.cache_misses}",
                "# HELP gateway_rate_limited_total Requests rejected by the rate limiter.",
                "# TYPE gateway_rate_limited_total counter",
                f"gateway_rate_limited_total {self.rate_limited_total}",
                "# HELP gateway_request_latency_seconds_sum Cumulative request latency.",
                "# TYPE gateway_request_latency_seconds_sum counter",
                f"gateway_request_latency_seconds_sum {self._latency_sum:.6f}",
                "# HELP gateway_request_latency_seconds_count Latency observation count.",
                "# TYPE gateway_request_latency_seconds_count counter",
                f"gateway_request_latency_seconds_count {self._latency_count}",
            ]
            return "\n".join(lines) + "\n"
