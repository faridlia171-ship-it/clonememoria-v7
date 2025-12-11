import logging
from typing import List, Dict, Any, Optional
import httpx
import time

from backend.ai.llm_provider import LLMProvider
from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("EXTERNAL_PROVIDER_LOADED", extra={"file": __file__})


class ExternalProvider(LLMProvider):
    """LLM provider that calls external APIs (OpenAI-compatible)."""

    def __init__(self):
        self.api_url = settings.LLM_API_URL or "https://api.openai.com/v1/chat/completions"
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

        logger.info("EXTERNAL_PROVIDER_INITIALIZED", extra={
            "api_url": self.api_url,
            "model": self.model,
            "has_api_key": bool(self.api_key)
        })

    async def generate_clone_reply(
        self,
        clone_info: Dict[str, Any],
        memories: List[Dict[str, Any]],
        conversation_history: List[Dict[str, str]],
        user_message: str,
        tone_config: Optional[Dict[str, float]] = None
    ) -> str:
        """Generate a response using external LLM API."""

        start_time = time.time()

        logger.info("EXTERNAL_PROVIDER_GENERATING_REPLY", extra={
            "clone_id": clone_info.get("id"),
            "clone_name": clone_info.get("name"),
            "user_message_length": len(user_message),
            "memories_count": len(memories),
            "history_length": len(conversation_history)
        })

        system_prompt = self._build_system_prompt(clone_info, memories, tone_config)

        logger.debug("SYSTEM_PROMPT_BUILT", extra={
            "prompt_length": len(system_prompt),
            "estimated_tokens": len(system_prompt) // 4
        })

        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(self._format_conversation_history(conversation_history))
        messages.append({"role": "user", "content": user_message})

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }

                payload = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 500
                }

                logger.info("LLM_API_REQUEST_SENT", extra={
                    "model": self.model,
                    "messages_count": len(messages),
                    "temperature": 0.7
                })

                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )

                response.raise_for_status()
                data = response.json()

                reply = data["choices"][0]["message"]["content"]

                elapsed_time = time.time() - start_time

                logger.info("LLM_API_RESPONSE_RECEIVED", extra={
                    "response_length": len(reply),
                    "elapsed_time": elapsed_time,
                    "clone_name": clone_info.get("name")
                })

                return reply

        except httpx.HTTPError as e:
            elapsed_time = time.time() - start_time

            logger.error("LLM_API_ERROR", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "elapsed_time": elapsed_time
            })

            return f"I'm having trouble expressing myself right now. Please try again in a moment."

        except Exception as e:
            elapsed_time = time.time() - start_time

            logger.error("LLM_GENERATION_ERROR", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "elapsed_time": elapsed_time
            }, exc_info=True)

            return "I'm experiencing some difficulties. Can we talk again soon?"
