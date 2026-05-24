"""Provider interface that all backend adapters implement."""

from __future__ import annotations

import abc

from llm_gateway.schemas import ChatCompletionRequest, ChatCompletionResponse


class Provider(abc.ABC):
    """A backend that can fulfil a chat completion request."""

    name: str

    @abc.abstractmethod
    async def chat_completion(
        self, request: ChatCompletionRequest
    ) -> ChatCompletionResponse:  # pragma: no cover - interface
        ...
