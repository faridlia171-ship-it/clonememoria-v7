import logging
from pydantic import BaseModel

logger = logging.getLogger(__name__)
logger.info("AVATAR_SCHEMAS_LOADED", extra={"file": __file__})


class AvatarUploadResponse(BaseModel):
    """Response after uploading an avatar image."""
    avatar_image_url: str
    message: str = "Avatar uploaded successfully"

    class Config:
        from_attributes = True
