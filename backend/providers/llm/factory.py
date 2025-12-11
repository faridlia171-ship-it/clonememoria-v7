import logging
from typing import Optional

from backend.providers.llm.base import BaseLLMProvider
from backend.providers.llm.dummy import DummyLLMProvider
from backend.providers.llm.openai_like import OpenAILikeLLMProvider
from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("LLM_FACTORY_LOADED", extra={"file": __file__})


def get_llm_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None
) -> BaseLLMProvider:
    """
    Factory function to get the appropriate LLM provider.

    Args:
        provider_name: Override provider (e.g., "dummy", "openai")
        model: Override model name

    Returns:
        Configured LLM provider instance
    """
    provider = provider_name or getattr(settings, 'LLM_DEFAULT_PROVIDER', 'dummy')

    logger.info("GETTING_LLM_PROVIDER", extra={
        "provider": provider,
        "model": model
    })

    if provider == "dummy":
        return DummyLLMProvider()
    elif provider == "openai":
        return OpenAILikeLLMProvider(model=model)
    else:
        logger.warning("UNKNOWN_LLM_PROVIDER_FALLBACK", extra={
            "requested_provider": provider
        })
        return DummyLLMProvider()
