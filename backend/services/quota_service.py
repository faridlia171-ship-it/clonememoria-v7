import logging
from typing import Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


async def get_user_quotas(db_client, user_id: str, billing_plan: str) -> dict:
    """
    Get user's quotas based on their billing plan.

    Returns:
        Dict with quota limits
    """
    try:
        result = await db_client.from_("billing_quotas").select("*").eq(
            "plan", billing_plan
        ).maybe_single().execute()

        if not result.data:
            logger.warning(
                "Quota plan not found, using FREE defaults",
                extra={"user_id": user_id, "plan": billing_plan}
            )
            return {
                "max_clones": 2,
                "max_messages_per_month": 100,
                "max_documents_per_clone": 5
            }

        return {
            "max_clones": result.data["max_clones"],
            "max_messages_per_month": result.data["max_messages_per_month"],
            "max_documents_per_clone": result.data["max_documents_per_clone"]
        }

    except Exception as e:
        logger.error(
            "Error fetching quotas",
            extra={"user_id": user_id, "error": str(e)}
        )
        return {
            "max_clones": 2,
            "max_messages_per_month": 100,
            "max_documents_per_clone": 5
        }


async def check_clone_creation_quota(
    db_client,
    user_id: str,
    billing_plan: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if user can create a new clone based on their quota.

    Returns:
        Tuple of (is_allowed, error_message)
    """
    try:
        quotas = await get_user_quotas(db_client, user_id, billing_plan)
        max_clones = quotas["max_clones"]

        count_result = await db_client.rpc(
            "get_user_clone_count",
            {"p_user_id": user_id}
        ).execute()

        current_count = count_result.data if count_result.data else 0

        if current_count >= max_clones:
            error_msg = f"Clone creation limit reached. Your {billing_plan} plan allows {max_clones} clones. Upgrade to create more."
            logger.warning(
                "Clone creation quota exceeded",
                extra={
                    "user_id": user_id,
                    "current_count": current_count,
                    "max_clones": max_clones
                }
            )
            return False, error_msg

        logger.info(
            "Clone creation quota check passed",
            extra={
                "user_id": user_id,
                "current_count": current_count,
                "max_clones": max_clones
            }
        )
        return True, None

    except Exception as e:
        logger.error(
            "Error checking clone quota",
            extra={"user_id": user_id, "error": str(e)}
        )
        return True, None


async def check_message_quota(
    db_client,
    user_id: str,
    billing_plan: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if user can send a new message based on monthly quota.

    Returns:
        Tuple of (is_allowed, error_message)
    """
    try:
        quotas = await get_user_quotas(db_client, user_id, billing_plan)
        max_messages = quotas["max_messages_per_month"]

        count_result = await db_client.rpc(
            "get_user_message_count_this_month",
            {"p_user_id": user_id}
        ).execute()

        current_count = count_result.data if count_result.data else 0

        if current_count >= max_messages:
            error_msg = f"Monthly message limit reached. Your {billing_plan} plan allows {max_messages} messages per month. Upgrade for more."
            logger.warning(
                "Message quota exceeded",
                extra={
                    "user_id": user_id,
                    "current_count": current_count,
                    "max_messages": max_messages
                }
            )
            return False, error_msg

        logger.debug(
            "Message quota check passed",
            extra={
                "user_id": user_id,
                "current_count": current_count,
                "max_messages": max_messages
            }
        )
        return True, None

    except Exception as e:
        logger.error(
            "Error checking message quota",
            extra={"user_id": user_id, "error": str(e)}
        )
        return True, None


async def check_document_quota(
    db_client,
    clone_id: str,
    user_id: str,
    billing_plan: str
) -> Tuple[bool, Optional[str]]:
    """
    Check if user can add a new document to a clone based on quota.

    Returns:
        Tuple of (is_allowed, error_message)
    """
    try:
        quotas = await get_user_quotas(db_client, user_id, billing_plan)
        max_documents = quotas["max_documents_per_clone"]

        count_result = await db_client.rpc(
            "get_clone_document_count",
            {"p_clone_id": clone_id}
        ).execute()

        current_count = count_result.data if count_result.data else 0

        if current_count >= max_documents:
            error_msg = f"Document limit reached for this clone. Your {billing_plan} plan allows {max_documents} documents per clone. Upgrade for more."
            logger.warning(
                "Document quota exceeded",
                extra={
                    "user_id": user_id,
                    "clone_id": clone_id,
                    "current_count": current_count,
                    "max_documents": max_documents
                }
            )
            return False, error_msg

        logger.debug(
            "Document quota check passed",
            extra={
                "user_id": user_id,
                "clone_id": clone_id,
                "current_count": current_count,
                "max_documents": max_documents
            }
        )
        return True, None

    except Exception as e:
        logger.error(
            "Error checking document quota",
            extra={"user_id": user_id, "error": str(e)}
        )
        return True, None


async def get_user_usage_stats(db_client, user_id: str, billing_plan: str) -> dict:
    """
    Get current usage statistics for a user.

    Returns:
        Dict with usage stats and quotas
    """
    try:
        quotas = await get_user_quotas(db_client, user_id, billing_plan)

        clone_count_result = await db_client.rpc(
            "get_user_clone_count",
            {"p_user_id": user_id}
        ).execute()
        clone_count = clone_count_result.data if clone_count_result.data else 0

        message_count_result = await db_client.rpc(
            "get_user_message_count_this_month",
            {"p_user_id": user_id}
        ).execute()
        message_count = message_count_result.data if message_count_result.data else 0

        return {
            "clones": {
                "current": clone_count,
                "max": quotas["max_clones"],
                "percentage": (clone_count / quotas["max_clones"] * 100) if quotas["max_clones"] > 0 else 0
            },
            "messages_this_month": {
                "current": message_count,
                "max": quotas["max_messages_per_month"],
                "percentage": (message_count / quotas["max_messages_per_month"] * 100) if quotas["max_messages_per_month"] > 0 else 0
            },
            "billing_plan": billing_plan
        }

    except Exception as e:
        logger.error(
            "Error getting usage stats",
            extra={"user_id": user_id, "error": str(e)}
        )
        return {
            "clones": {"current": 0, "max": 2, "percentage": 0},
            "messages_this_month": {"current": 0, "max": 100, "percentage": 0},
            "billing_plan": billing_plan
        }
