import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger(__name__)
logger.info("TTS_BASE_PROVIDER_LOADED", extra={"file": __file__})


class BaseTTSProvider(ABC):
    """Base class for TTS (Text-to-Speech) providers."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: Optional[str] = None
    ) -> bytes:
        """
        Synthesize speech from text.

        Args:
            text: Text to convert to speech
            voice_id: Optional voice identifier

        Returns:
            Audio bytes (typically MP3 or WAV format)
        """
        pass
