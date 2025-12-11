import logging
from typing import Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
logger.info("AI_CONFIG_SCHEMAS_LOADED", extra={"file": __file__})


class AIConfigUpdate(BaseModel):
    """Schema for updating clone AI configuration."""
    llm_provider: Optional[str] = Field(None, pattern="^(dummy|openai)$")
    llm_model: Optional[str] = None
    embedding_provider: Optional[str] = Field(None, pattern="^(dummy|openai)$")
    tts_provider: Optional[str] = Field(None, pattern="^(dummy|external)$")
    tts_voice_id: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=32000)


class TTSRequest(BaseModel):
    """Schema for TTS synthesis request."""
    text: str = Field(..., min_length=1, max_length=5000)
