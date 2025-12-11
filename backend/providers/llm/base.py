import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

logger = logging.getLogger(__name__)
logger.info("LLM_BASE_PROVIDER_LOADED", extra={"file": __file__})


class BaseLLMProvider(ABC):
    """Base class for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        messages: Optional[list[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """
        Generate a complete response.

        Args:
            prompt: User prompt/message
            system: System prompt
            messages: Full conversation history
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        messages: Optional[list[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response.

        Args:
            prompt: User prompt/message
            system: System prompt
            messages: Full conversation history
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0-1)

        Yields:
            Text chunks as they are generated
        """
        pass
