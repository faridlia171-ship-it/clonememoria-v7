import logging
from typing import Optional

from backend.providers.tts.base import BaseTTSProvider
from backend.providers.tts.dummy import DummyTTSProvider
from backend.providers.tts.external import ExternalTTSProvider
from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("TTS_FACTORY_LOADED", extra={"file": __file__})


def get_tts_provider(
    provider_name: Optional[str] = None
) -> BaseTTSProvider:
    """
    Factory function to get the appropriate TTS provider.

    Args:
        provider_name: Override provider (e.g., "dummy", "external")

    Returns:
        Configured TTS provider instance
    """
    provider = provider_name or getattr(settings, 'TTS_DEFAULT_PROVIDER', 'dummy')

    logger.info("GETTING_TTS_PROVIDER", extra={
        "provider": provider
    })

    if provider == "dummy":
        return DummyTTSProvider()
    elif provider == "external":
        return ExternalTTSProvider()
    else:
        logger.warning("UNKNOWN_TTS_PROVIDER_FALLBACK", extra={
            "requested_provider": provider
        })
        return DummyTTSProvider()
