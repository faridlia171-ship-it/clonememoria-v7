import logging
from typing import Optional
import httpx

from backend.providers.embeddings.base import BaseEmbeddingProvider
from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("OPENAI_LIKE_EMBEDDINGS_PROVIDER_LOADED", extra={"file": __file__})


class OpenAILikeEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI-compatible embedding provider using httpx."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.base_url = base_url or getattr(settings, 'EMBEDDINGS_OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.api_key = api_key or getattr(settings, 'EMBEDDINGS_OPENAI_API_KEY', '')
        self.model = model or getattr(settings, 'EMBEDDINGS_OPENAI_MODEL', 'text-embedding-3-small')
        self._dimension = 1536

        logger.info("OPENAI_LIKE_EMBEDDINGS_PROVIDER_INITIALIZED", extra={
            "base_url": self.base_url,
            "model": self.model,
            "has_api_key": bool(self.api_key)
        })

    def get_dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings using OpenAI-compatible API."""
        logger.info("OPENAI_LIKE_EMBEDDINGS_EMBED", extra={
            "text_count": len(texts),
            "model": self.model
        })

        payload = {
            "model": self.model,
            "input": texts
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    json=payload,
                    headers=headers
                )

                response.raise_for_status()
                data = response.json()

                embeddings = [item["embedding"] for item in data["data"]]

                if embeddings and len(embeddings[0]) != self._dimension:
                    self._dimension = len(embeddings[0])

                logger.info("OPENAI_LIKE_EMBEDDINGS_EMBED_COMPLETE", extra={
                    "embeddings_count": len(embeddings),
                    "dimension": self._dimension
                })

                return embeddings

        except httpx.HTTPError as e:
            logger.error("OPENAI_LIKE_EMBEDDINGS_EMBED_ERROR", extra={
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise Exception(f"Embeddings API error: {str(e)}")
