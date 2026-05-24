"""OpenAI backend adapter.

Activates only when an OpenAI API key is configured. Tests mock the HTTP layer
(respx) so no network access or real key is required.
"""

from __future__ import annotations

import httpx

from llm_gateway.providers.base import Provider
from llm_gateway.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
)


class OpenAIProvider(Provider):
    name = "openai"

    def __init__(self, api_key: str, base_url: str, timeout: float = 30.0) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        payload = request.model_dump(exclude_none=True)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            return ChatCompletionResponse.model_validate(resp.json())
