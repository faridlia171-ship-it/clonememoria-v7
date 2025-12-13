import logging
from typing import Dict
from supabase import create_client
from backend.core.config import settings

logger = logging.getLogger(__name__)
supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


class UserService:

    @staticmethod
    def update_consent(user_id: str, consent: Dict):
        logger.info("UPDATING_USER_CONSENT", extra={"user_id": user_id})

        data = {
            "user_id": user_id,
            "marketing": consent.get("marketing", False),
            "analytics": consent.get("analytics", False),
        }

        result = supabase.table("user_consent").upsert(data).execute()

        return result.data
