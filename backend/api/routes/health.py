import logging
from fastapi import APIRouter, Depends
from supabase import Client

from backend.db.client import get_db
from backend.core.config import settings

logger = logging.getLogger(__name__)
logger.info("HEALTH_ROUTES_LOADED", extra={"file": __file__})

router = APIRouter()


@router.get("/health")
async def health_check(db: Client = Depends(get_db)):
    """Health check endpoint - verifies database connectivity."""

    logger.debug("HEALTH_CHECK_REQUEST")

    try:
        result = db.table("users").select("id").limit(1).execute()

        logger.info("HEALTH_CHECK_SUCCESS")

        return {
            "status": "ok",
            "database": "connected",
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION
        }

    except Exception as e:
        logger.error("HEALTH_CHECK_FAILED", extra={
            "error": str(e)
        })

        return {
            "status": "error",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/metrics")
async def get_metrics(db: Client = Depends(get_db)):
    """Basic metrics endpoint - returns usage statistics."""

    logger.debug("METRICS_REQUEST")

    try:
        users_count = db.table("users").select("id", count="exact").execute().count or 0
        clones_count = db.table("clones").select("id", count="exact").execute().count or 0
        conversations_count = db.table("conversations").select("id", count="exact").execute().count or 0
        messages_count = db.table("messages").select("id", count="exact").execute().count or 0
        documents_count = db.table("clone_documents").select("id", count="exact").execute().count or 0

        logger.info("METRICS_SUCCESS", extra={
            "users": users_count,
            "clones": clones_count,
            "conversations": conversations_count
        })

        return {
            "users": users_count,
            "clones": clones_count,
            "conversations": conversations_count,
            "messages": messages_count,
            "documents": documents_count
        }

    except Exception as e:
        logger.error("METRICS_FAILED", extra={
            "error": str(e)
        })

        return {
            "error": str(e)
        }
