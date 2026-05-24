"""Deterministic echo/mock provider.

This is the default provider so the gateway is fully functional offline with
zero external dependencies. It echoes the last user message back, which makes
responses deterministic and trivially testable.
"""

from __future__ import annotations

from llm_gateway.providers.base import Provider
from llm_gateway.schemas import (
    ChatCompletionChoice,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Usage,
)


def _count_tokens(text: str) -> int:
    """Cheap, deterministic token estimate (whitespace words)."""
    return len(text.split())


class EchoProvider(Provider):
    name = "echo"

    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        last_user = next(
            (m.content for m in reversed(request.messages) if m.role == "user"),
            "",
        )
        reply = f"echo: {last_user}"
        prompt_tokens = sum(_count_tokens(m.content) for m in request.messages)
        completion_tokens = _count_tokens(reply)
        return ChatCompletionResponse(
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=reply),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )
