from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID
import logging
from supabase import Client

from backend.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from backend.schemas.tokens import TokenPair, RefreshTokenCreate

logger = logging.getLogger(__name__)


class TokenService:
    def __init__(self, db: Client):
        self.db = db

    def create_token_pair(
        self,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        device_info: Dict[str, Any] = None
    ) -> TokenPair:
        try:
            access_token = create_access_token(data={"sub": str(user_id)})
            refresh_token_jwt = create_refresh_token(data={"sub": str(user_id)})

            refresh_token_hash = hash_token(refresh_token_jwt)
            expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

            refresh_token_data = {
                "user_id": str(user_id),
                "token_hash": refresh_token_hash,
                "expires_at": expires_at.isoformat(),
                "device_info": device_info or {},
                "ip_address": ip_address,
                "user_agent": user_agent
            }

            self.db.table('refresh_tokens').insert(refresh_token_data).execute()

            logger.info(f"Token pair created for user {user_id}")

            return TokenPair(
                access_token=access_token,
                refresh_token=refresh_token_jwt,
                token_type="bearer",
                expires_in=1800
            )

        except Exception as e:
            logger.error(f"Failed to create token pair: {str(e)}")
            raise

    def refresh_access_token(
        self,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> TokenPair:
        try:
            payload = decode_refresh_token(refresh_token)
            user_id = UUID(payload.get("sub"))

            token_hash = hash_token(refresh_token)

            if self.is_token_blacklisted(token_hash):
                logger.warning(f"Attempt to use blacklisted token for user {user_id}")
                raise Exception("Token has been revoked")

            stored_token = self.db.table('refresh_tokens') \
                .select('*') \
                .eq('token_hash', token_hash) \
                .is_('revoked_at', 'null') \
                .maybeSingle() \
                .execute()

            if not stored_token.data:
                logger.warning(f"Refresh token not found or revoked for user {user_id}")
                raise Exception("Invalid refresh token")

            if datetime.fromisoformat(stored_token.data['expires_at'].replace('Z', '+00:00')) < datetime.utcnow():
                logger.warning(f"Expired refresh token for user {user_id}")
                raise Exception("Refresh token expired")

            new_token_pair = self.create_token_pair(
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent
            )

            self.db.table('refresh_tokens') \
                .update({
                    'revoked_at': datetime.utcnow().isoformat(),
                    'replaced_by_token_id': None
                }) \
                .eq('token_hash', token_hash) \
                .execute()

            logger.info(f"Access token refreshed for user {user_id}")

            return new_token_pair

        except Exception as e:
            logger.error(f"Failed to refresh token: {str(e)}")
            raise

    def revoke_token(self, token: str, reason: str = "manual_revoke") -> bool:
        try:
            token_hash = hash_token(token)
            payload = decode_refresh_token(token)
            user_id = payload.get("sub")
            expires_at = datetime.fromtimestamp(payload.get("exp"))

            self.db.table('token_blacklist').insert({
                "token_hash": token_hash,
                "user_id": user_id,
                "expires_at": expires_at.isoformat(),
                "reason": reason
            }).execute()

            self.db.table('refresh_tokens') \
                .update({'revoked_at': datetime.utcnow().isoformat()}) \
                .eq('token_hash', token_hash) \
                .execute()

            logger.info(f"Token revoked for user {user_id}, reason: {reason}")
            return True

        except Exception as e:
            logger.error(f"Failed to revoke token: {str(e)}")
            return False

    def revoke_all_user_tokens(self, user_id: UUID, reason: str = "logout_all") -> int:
        try:
            result = self.db.table('refresh_tokens') \
                .update({'revoked_at': datetime.utcnow().isoformat()}) \
                .eq('user_id', str(user_id)) \
                .is_('revoked_at', 'null') \
                .execute()

            count = len(result.data) if result.data else 0
            logger.info(f"Revoked {count} tokens for user {user_id}, reason: {reason}")
            return count

        except Exception as e:
            logger.error(f"Failed to revoke user tokens: {str(e)}")
            return 0

    def is_token_blacklisted(self, token_hash: str) -> bool:
        try:
            result = self.db.rpc('is_token_blacklisted', {'p_token_hash': token_hash}).execute()
            return result.data if result.data is not None else False

        except Exception as e:
            logger.error(f"Failed to check token blacklist: {str(e)}")
            return False

    def cleanup_expired_tokens(self) -> Dict[str, int]:
        try:
            self.db.rpc('cleanup_expired_tokens').execute()

            logger.info("Expired tokens cleaned up")
            return {"status": "success"}

        except Exception as e:
            logger.error(f"Failed to cleanup tokens: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_user_sessions(self, user_id: UUID):
        try:
            result = self.db.table('refresh_tokens') \
                .select('id, created_at, device_info, ip_address, last_used_at, revoked_at') \
                .eq('user_id', str(user_id)) \
                .is_('revoked_at', 'null') \
                .order('created_at', desc=True) \
                .execute()

            return result.data

        except Exception as e:
            logger.error(f"Failed to get user sessions: {str(e)}")
            return []
