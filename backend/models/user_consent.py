import logging
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
logger.info("USER_CONSENT_MODEL_LOADED", extra={"file": __file__})


class UserConsent(BaseModel):
    marketing: bool = False
    analytics: bool = False
    updated_at: Optional[datetime] = None
