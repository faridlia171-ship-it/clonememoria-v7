import logging
from typing import List, Dict, Any, Optional
import random

from backend.ai.llm_provider import LLMProvider

logger = logging.getLogger(__name__)
logger.info("DUMMY_PROVIDER_LOADED", extra={"file": __file__})


class DummyProvider(LLMProvider):
    """Dummy LLM provider for testing without external API calls."""

    RESPONSE_TEMPLATES = [
        "I remember that time... it brings back such warm feelings.",
        "You know, thinking about what you said, I can't help but smile.",
        "That reminds me of something important we shared together.",
        "I'm so glad you brought that up. It means a lot to me.",
        "Let me tell you what I think about that...",
        "Your words always had a way of touching my heart.",
        "I've been thinking about this quite a bit lately.",
        "You always knew how to make me see things differently."
    ]

    async def generate_clone_reply(
        self,
        clone_info: Dict[str, Any],
        memories: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        user_message: str,
        tone_config: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate a dummy response for testing."""

        logger.info("DUMMY_PROVIDER_GENERATING_REPLY", extra={
            "clone_name": clone_info.get("name"),
            "user_message_length": len(user_message),
            "memories_count": len(memories),
            "history_length": len(conversation_history)
        })

        clone_name = clone_info.get("name", "Unknown")
        tone = tone_config or {"warmth": 0.7, "humor": 0.5, "formality": 0.3}

        base_response = random.choice(self.RESPONSE_TEMPLATES)

        if memories and random.random() > 0.5:
            memory = random.choice(memories)
            memory_ref = f" I'm thinking of {memory.get('title', 'that moment')}."
            base_response += memory_ref

        if tone["humor"] > 0.6 and random.random() > 0.7:
            base_response += " *chuckles*"

        if tone["warmth"] > 0.6:
            base_response += f" You know how much you mean to me."

        logger.info("DUMMY_PROVIDER_RESPONSE_GENERATED", extra={
            "response_length": len(base_response),
            "clone_name": clone_name
        })

        return base_response
