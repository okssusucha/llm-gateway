"""Configuration loaded from environment variables.

The gateway is fully functional offline: with no provider keys set it falls
back to the deterministic ``echo`` provider, so it works with zero external
dependencies (CI-safe).
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GATEWAY_", env_file=".env", extra="ignore")

    # Gateway-issued API keys (comma-separated). Clients authenticate with one
    # of these via the Authorization: Bearer header.
    api_keys: str = "demo-key"

    # Default provider used when a model has no explicit route. "echo" keeps the
    # gateway working offline with deterministic responses.
    default_provider: str = "echo"

    # Real provider credentials. When unset, those providers are simply
    # unavailable and routing falls back to the default (echo) provider.
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str | None = None
    anthropic_base_url: str = "https://api.anthropic.com/v1"

    # Per-key token-bucket rate limiting.
    rate_limit_capacity: int = 60
    rate_limit_refill_per_sec: float = 1.0

    # Response caching. Uses an in-memory cache by default; if redis_url is set
    # and the redis client is installed, a Redis-backed cache is used instead.
    cache_enabled: bool = True
    cache_ttl_seconds: int = 300
    redis_url: str | None = None

    def parsed_api_keys(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Clear the cached settings (used by tests)."""
    global _settings
    _settings = None
