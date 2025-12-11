import logging
import json
from typing import AsyncIterator, Optional
import httpx

from backend.providers.llm.base import BaseLLMProvider
from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("OPENAI_LIKE_LLM_PROVIDER_LOADED", extra={"file": __file__})


class OpenAILikeLLMProvider(BaseLLMProvider):
    """OpenAI-compatible LLM provider using httpx."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.base_url = base_url or getattr(settings, 'LLM_OPENAI_BASE_URL', 'https://api.openai.com/v1')
        self.api_key = api_key or getattr(settings, 'LLM_OPENAI_API_KEY', '')
        self.model = model or getattr(settings, 'LLM_OPENAI_MODEL', 'gpt-3.5-turbo')

        logger.info("OPENAI_LIKE_LLM_PROVIDER_INITIALIZED", extra={
            "base_url": self.base_url,
            "model": self.model,
            "has_api_key": bool(self.api_key)
        })

    def _build_messages(
        self,
        prompt: str,
        system: Optional[str] = None,
        messages: Optional[list[dict]] = None
    ) -> list[dict]:
        """Build messages array for API call."""
        result = []

        if system:
            result.append({"role": "system", "content": system})

        if messages:
            result.extend(messages)

        result.append({"role": "user", "content": prompt})

        return result

    async def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        messages: Optional[list[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> str:
        """Generate response using OpenAI-compatible API."""
        logger.info("OPENAI_LIKE_LLM_GENERATE", extra={
            "prompt_length": len(prompt),
            "model": self.model
        })

        api_messages = self._build_messages(prompt, system, messages)

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature or 0.7,
            "stream": False
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                )

                response.raise_for_status()
                data = response.json()

                content = data["choices"][0]["message"]["content"]

                logger.info("OPENAI_LIKE_LLM_GENERATE_COMPLETE", extra={
                    "response_length": len(content)
                })

                return content

        except httpx.HTTPError as e:
            logger.error("OPENAI_LIKE_LLM_GENERATE_ERROR", extra={
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise Exception(f"LLM API error: {str(e)}")

    async def stream(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        messages: Optional[list[dict]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncIterator[str]:
        """Stream response using OpenAI-compatible API."""
        logger.info("OPENAI_LIKE_LLM_STREAM_START", extra={
            "prompt_length": len(prompt),
            "model": self.model
        })

        api_messages = self._build_messages(prompt, system, messages)

        payload = {
            "model": self.model,
            "messages": api_messages,
            "temperature": temperature or 0.7,
            "stream": True
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]

                            if data_str == "[DONE]":
                                break

                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")

                                if content:
                                    yield content

                            except json.JSONDecodeError:
                                continue

            logger.info("OPENAI_LIKE_LLM_STREAM_COMPLETE")

        except httpx.HTTPError as e:
            logger.error("OPENAI_LIKE_LLM_STREAM_ERROR", extra={
                "error": str(e),
                "error_type": type(e).__name__
            })
            raise Exception(f"LLM streaming error: {str(e)}")
