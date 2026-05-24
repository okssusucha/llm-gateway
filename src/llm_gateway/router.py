"""Provider routing by model name.

A model prefix selects a provider (``openai/...``, ``anthropic/...``,
``echo/...``). Bare OpenAI-style names (``gpt-*``) route to OpenAI when a key is
configured. Anything else — and anything whose provider key is missing — falls
back to the default (echo) provider, keeping the gateway usable offline.
"""

from __future__ import annotations

from llm_gateway.config import Settings
from llm_gateway.providers.anthropic import AnthropicProvider
from llm_gateway.providers.base import Provider
from llm_gateway.providers.echo import EchoProvider
from llm_gateway.providers.openai import OpenAIProvider


class ProviderRouter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._echo = EchoProvider()
        self._providers: dict[str, Provider] = {"echo": self._echo}

        if settings.openai_api_key:
            self._providers["openai"] = OpenAIProvider(
                settings.openai_api_key, settings.openai_base_url
            )
        if settings.anthropic_api_key:
            self._providers["anthropic"] = AnthropicProvider(
                settings.anthropic_api_key, settings.anthropic_base_url
            )

    def available(self) -> list[str]:
        return sorted(self._providers)

    def _provider_for(self, model: str) -> str:
        if "/" in model:
            return model.split("/", 1)[0]
        if model.startswith(("gpt-", "o1", "o3")):
            return "openai"
        if model.startswith("claude"):
            return "anthropic"
        return self._settings.default_provider

    def resolve(self, model: str) -> Provider:
        """Return the provider for a model, falling back to echo if unavailable."""
        name = self._provider_for(model)
        return self._providers.get(name) or self._providers.get(
            self._settings.default_provider, self._echo
        )
