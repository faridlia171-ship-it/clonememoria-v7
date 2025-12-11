import logging
from typing import Optional

from backend.providers.embeddings.base import BaseEmbeddingProvider
from backend.providers.embeddings.dummy import DummyEmbeddingProvider
from backend.providers.embeddings.openai_like import OpenAILikeEmbeddingProvider
from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("EMBEDDINGS_FACTORY_LOADED", extra={"file": __file__})


def get_embedding_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None
) -> BaseEmbeddingProvider:
    """
    Factory function to get the appropriate embedding provider.

    Args:
        provider_name: Override provider (e.g., "dummy", "openai")
        model: Override model name

    Returns:
        Configured embedding provider instance
    """
    provider = provider_name or getattr(settings, 'EMBEDDINGS_DEFAULT_PROVIDER', 'dummy')

    logger.info("GETTING_EMBEDDINGS_PROVIDER", extra={
        "provider": provider,
        "model": model
    })

    if provider == "dummy":
        return DummyEmbeddingProvider()
    elif provider == "openai":
        return OpenAILikeEmbeddingProvider(model=model)
    else:
        logger.warning("UNKNOWN_EMBEDDINGS_PROVIDER_FALLBACK", extra={
            "requested_provider": provider
        })
        return DummyEmbeddingProvider()
