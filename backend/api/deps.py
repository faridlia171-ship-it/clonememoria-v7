import logging
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from supabase import Client

from backend.core.config import settings
from backend.db.client import get_db

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# ============================================================
# AUTH – TOKEN EXTRACTION
# ============================================================

def get_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return credentials.credentials


# ============================================================
# AUTH – CURRENT USER ID
# ============================================================

def get_current_user_id(
    token: str = Depends(get_token),
) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        user_id: Optional[str] = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        return user_id

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )


# ============================================================
# AUTH – CURRENT USER (FULL OBJECT)
# ============================================================

def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
) -> dict:
    result = (
        db.table("users")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return result.data[0]


# ============================================================
# CLONES – OWNERSHIP VERIFICATION (CRITICAL FIX)
# ============================================================

def verify_clone_ownership(
    request: Request,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db),
) -> dict:
    clone_id = request.path_params.get("clone_id")

    if not clone_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing clone_id",
        )

    # Tentative de propagation du contexte utilisateur (RLS-friendly)
    try:
        db.rpc(
            "set_config",
            {
                "setting": "app.current_user_id",
                "value": user_id,
                "is_local": True,
            },
        ).execute()
    except Exception:
        pass

    # ⚠️ IMPORTANT :
    # - PAS de maybe_single()
    # - PAS d'exception PostgREST 204
    result = (
        db.table("clones")
        .select("*")
        .eq("id", clone_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clone not found",
        )

    return result.data[0]
