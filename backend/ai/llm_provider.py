import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)
logger.info("LLM_PROVIDER_MODULE_LOADED", extra={"file": __file__})


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate_clone_reply(
        self,
        clone_info: Dict[str, Any],
        memories: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        user_message: str,
        tone_config: Optional[Dict[str, float]] = None
    ) -> str:
        """
        Generate a reply from the clone based on context.

        Args:
            clone_info: Information about the clone (name, description, etc.)
            memories: List of relevant memories
            conversation_history: Recent conversation messages
            user_message: The user's current message
            tone_config: Tone configuration (warmth, humor, formality)

        Returns:
            The generated response text
        """
        pass

    def _build_system_prompt(
        self,
        clone_info: Dict[str, Any],
        memories: List[Dict[str, Any]],
        tone_config: Optional[Dict[str, float]] = None
    ) -> str:
        """Build the system prompt for the LLM."""
        tone = tone_config or {"warmth": 0.7, "humor": 0.5, "formality": 0.3}

        warmth_desc = "very warm and affectionate" if tone["warmth"] > 0.7 else \
                      "moderately warm" if tone["warmth"] > 0.4 else "neutral and composed"

        humor_desc = "frequently humorous and playful" if tone["humor"] > 0.7 else \
                     "occasionally humorous" if tone["humor"] > 0.4 else "serious and focused"

        formality_desc = "very formal and professional" if tone["formality"] > 0.7 else \
                         "moderately formal" if tone["formality"] > 0.4 else "casual and relaxed"

        memories_text = ""
        if memories:
            memories_text = "\n\nKey Memories:\n"
            for i, memory in enumerate(memories[:5], 1):
                memories_text += f"{i}. {memory.get('title', 'Untitled')}: {memory.get('content', '')[:200]}...\n"

        prompt = f"""You are simulating {clone_info['name']}, a person being remembered through this AI system.

Description: {clone_info.get('description', 'No description provided')}

Personality Traits:
- Communication style: {warmth_desc}
- Humor level: {humor_desc}
- Formality: {formality_desc}

{memories_text}

Instructions:
- Respond as {clone_info['name']} would, drawing from the memories and personality traits provided
- Keep responses natural, personal, and authentic to the character
- Show emotion and personality appropriate to the context
- Reference specific memories when relevant
- Maintain consistency with the described personality
- Keep responses concise but meaningful (2-4 sentences typically)
"""

        return prompt

    def _format_conversation_history(self, history: List[Dict[str, str]], limit: int = 10) -> List[Dict[str, str]]:
        """Format conversation history for the LLM."""
        recent_history = history[-limit:] if len(history) > limit else history

        formatted = []
        for msg in recent_history:
            role = "assistant" if msg["role"] == "clone" else msg["role"]
            formatted.append({
                "role": role,
                "content": msg["content"]
            })

        return formatted
