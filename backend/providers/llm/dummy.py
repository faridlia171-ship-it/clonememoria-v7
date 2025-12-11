import logging
import asyncio
from typing import AsyncIterator, Optional

from backend.providers.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)
logger.info("DUMMY_LLM_PROVIDER_LOADED", extra={"file": __file__})


class DummyLLMProvider(BaseLLMProvider):
    """Dummy LLM provider for testing without external API calls."""

    RESPONSES = [
        "I understand what you're saying, and it brings back memories.",
        "That's an interesting point. Let me think about that for a moment.",
        "You know, I've always felt that way too.",
        "I appreciate you sharing that with me.",
        "That reminds me of something we talked about before.",
        "I'm glad we can have these conversations.",
        "Tell me more about what you're thinking.",
        "I see where you're coming from on this."
    ]

    def __init__(self):
        logger.info("DUMMY_LLM_PROVIDER_INITIALIZED")

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        messages: Optional[list[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate a deterministic dummy response."""
        logger.info("DUMMY_LLM_GENERATE", extra={
            "prompt_length": len(prompt),
            "has_system": bool(system),
            "message_count": len(messages) if messages else 0
        })

        await asyncio.sleep(0.1)

        response_idx = hash(prompt) % len(self.RESPONSES)
        response = self.RESPONSES[response_idx]

        logger.info("DUMMY_LLM_GENERATE_COMPLETE", extra={
            "response_length": len(response)
        })

        return response

    async def stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        messages: Optional[list[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncIterator[str]:
        """Stream a dummy response word by word."""
        logger.info("DUMMY_LLM_STREAM_START", extra={
            "prompt_length": len(prompt)
        })

        response_idx = hash(prompt) % len(self.RESPONSES)
        response = self.RESPONSES[response_idx]

        words = response.split()

        for word in words:
            await asyncio.sleep(0.05)
            yield word + " "

        logger.info("DUMMY_LLM_STREAM_COMPLETE", extra={
            "token_count": len(words)
        })
