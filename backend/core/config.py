import os
from typing import Optional
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)
logger.info("CONFIG_MODULE_LOADED", extra={"file": __file__})


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    PROJECT_NAME: str = "CloneMemoria"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api"

    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    LLM_DEFAULT_PROVIDER: str = "dummy"
    LLM_PROVIDER: str = "dummy"
    LLM_API_URL: Optional[str] = None
    LLM_API_KEY: Optional[str] = None
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    LLM_OPENAI_API_KEY: Optional[str] = None
    LLM_OPENAI_MODEL: str = "gpt-3.5-turbo"

    EMBEDDINGS_DEFAULT_PROVIDER: str = "dummy"
    EMBEDDINGS_OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDINGS_OPENAI_API_KEY: Optional[str] = None
    EMBEDDINGS_OPENAI_MODEL: str = "text-embedding-3-small"

    TTS_DEFAULT_PROVIDER: str = "dummy"
    TTS_API_BASE_URL: Optional[str] = None
    TTS_API_KEY: Optional[str] = None
    TTS_DEFAULT_VOICE_ID: Optional[str] = None

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173"
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
logger.info("SETTINGS_LOADED", extra={
    "project_name": settings.PROJECT_NAME,
    "llm_provider": settings.LLM_PROVIDER,
    "log_level": settings.LOG_LEVEL
})
