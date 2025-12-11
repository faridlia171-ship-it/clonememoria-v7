import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)
logger.info("EMBEDDINGS_BASE_PROVIDER_LOADED", extra={"file": __file__})


class BaseEmbeddingProvider(ABC):
    """Base class for embedding providers."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (each vector is a list of floats)
        """
        pass

    @abstractmethod
    def get_dimension(self) -> int:
        """
        Get the dimension of the embedding vectors.

        Returns:
            Integer dimension of embeddings
        """
        pass
