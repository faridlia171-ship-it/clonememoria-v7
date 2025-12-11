import logging
from backend.ai.llm_provider import LLMProvider
from backend.ai.providers.dummy import DummyProvider
from backend.ai.providers.external import ExternalProvider
from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("AI_FACTORY_MODULE_LOADED", extra={"file": __file__})


def get_llm_provider() -> LLMProvider:
    """Factory function to get the configured LLM provider."""

    provider_type = settings.LLM_PROVIDER.lower()

    logger.info("GETTING_LLM_PROVIDER", extra={"provider_type": provider_type})

    if provider_type == "dummy":
        logger.info("USING_DUMMY_PROVIDER")
        return DummyProvider()
    elif provider_type in ["external", "openai"]:
        logger.info("USING_EXTERNAL_PROVIDER")
        return ExternalProvider()
    else:
        logger.warning("UNKNOWN_PROVIDER_TYPE_FALLBACK_TO_DUMMY", extra={
            "requested_provider": provider_type
        })
        return DummyProvider()
