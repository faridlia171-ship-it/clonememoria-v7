import logging
import hashlib
from typing import List

from backend.providers.embeddings.base import BaseEmbeddingProvider

logger = logging.getLogger(__name__)
logger.info("DUMMY_EMBEDDINGS_PROVIDER_LOADED", extra={"file": __file__})


class DummyEmbeddingProvider(BaseEmbeddingProvider):
    """Dummy embedding provider for testing without external API calls."""

    DIMENSION = 384

    def __init__(self):
        logger.info("DUMMY_EMBEDDINGS_PROVIDER_INITIALIZED", extra={
            "dimension": self.DIMENSION
        })

    def get_dimension(self) -> int:
        """Return embedding dimension."""
        return self.DIMENSION

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Generate deterministic dummy embeddings based on text hash.

        Creates a simple embedding by:
        1. Hashing the text
        2. Converting hash bytes to floats
        3. Normalizing to unit vector
        """
        logger.info("DUMMY_EMBEDDINGS_EMBED", extra={
            "text_count": len(texts),
            "dimension": self.DIMENSION
        })

        embeddings = []

        for text in texts:
            text_hash = hashlib.sha256(text.encode()).digest()

            vector = []
            for i in range(self.DIMENSION):
                byte_idx = i % len(text_hash)
                value = (text_hash[byte_idx] / 255.0) - 0.5
                vector.append(value)

            magnitude = sum(v * v for v in vector) ** 0.5
            if magnitude > 0:
                vector = [v / magnitude for v in vector]

            embeddings.append(vector)

        logger.info("DUMMY_EMBEDDINGS_EMBED_COMPLETE", extra={
            "embeddings_count": len(embeddings)
        })

        return embeddings
