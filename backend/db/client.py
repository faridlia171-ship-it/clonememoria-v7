import logging
from supabase import create_client, Client
from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("DB_CLIENT_MODULE_LOADED", extra={"file": __file__})


class DatabaseClient:
    """Supabase database client wrapper."""

    _instance: Client = None

    @classmethod
    def get_client(cls) -> Client:
        """Get Supabase client instance (singleton pattern)."""
        if cls._instance is None:
            logger.info("CREATING_SUPABASE_CLIENT", extra={
                "supabase_url": settings.SUPABASE_URL[:30] + "..."
            })

            cls._instance = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_ROLE_KEY
            )

            logger.info("SUPABASE_CLIENT_CREATED")

        return cls._instance


def get_db() -> Client:
    """Dependency for getting database client."""
    return DatabaseClient.get_client()
