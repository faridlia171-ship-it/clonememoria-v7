import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timedelta

from api.deps import get_current_admin, get_db_client
from schemas.admin import (
    AdminUserSummary,
    AdminCloneSummary,
    PlatformStats
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=List[AdminUserSummary])
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    admin: dict = Depends(get_current_admin),
    db=Depends(get_db_client)
):
    """List all users with statistics (admin only)."""
    try:
        result = await db.from_("users").select(
            "id, email, full_name, role, billing_plan, created_at"
        ).range(skip, skip + limit - 1).order("created_at", desc=True).execute()

        users_with_stats = []
        for user in result.data:
            clone_count_result = await db.rpc(
                "get_user_clone_count",
                {"p_user_id": user["id"]}
            ).execute()
            clone_count = clone_count_result.data if clone_count_result.data else 0

            message_count_result = await db.rpc(
                "get_user_message_count_this_month",
                {"p_user_id": user["id"]}
            ).execute()
            message_count = message_count_result.data if message_count_result.data else 0

            users_with_stats.append(AdminUserSummary(
                **user,
                clone_count=clone_count,
                message_count_this_month=message_count
            ))

        logger.info(
            "Admin listed users",
            extra={"admin_id": admin["id"], "count": len(users_with_stats)}
        )

        return users_with_stats

    except Exception as e:
        logger.error(
            "Error listing users for admin",
            extra={"admin_id": admin["id"], "error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Failed to list users")


@router.get("/clones", response_model=List[AdminCloneSummary])
async def list_all_clones(
    skip: int = 0,
    limit: int = 100,
    admin: dict = Depends(get_current_admin),
    db=Depends(get_db_client)
):
    """List all clones with statistics (admin only)."""
    try:
        result = await db.from_("clones").select(
            "id, name, user_id, created_at"
        ).range(skip, skip + limit - 1).order("created_at", desc=True).execute()

        clones_with_stats = []
        for clone in result.data:
            user_result = await db.from_("users").select("email").eq(
                "id", clone["user_id"]
            ).maybe_single().execute()
            user_email = user_result.data["email"] if user_result.data else "unknown"

            memory_count_result = await db.from_("memories").select(
                "id", count="exact"
            ).eq("clone_id", clone["id"]).execute()
            memory_count = memory_count_result.count or 0

            conv_count_result = await db.from_("conversations").select(
                "id", count="exact"
            ).eq("clone_id", clone["id"]).execute()
            conv_count = conv_count_result.count or 0

            doc_count_result = await db.rpc(
                "get_clone_document_count",
                {"p_clone_id": clone["id"]}
            ).execute()
            doc_count = doc_count_result.data if doc_count_result.data else 0

            clones_with_stats.append(AdminCloneSummary(
                **clone,
                user_email=user_email,
                memory_count=memory_count,
                conversation_count=conv_count,
                document_count=doc_count
            ))

        logger.info(
            "Admin listed clones",
            extra={"admin_id": admin["id"], "count": len(clones_with_stats)}
        )

        return clones_with_stats

    except Exception as e:
        logger.error(
            "Error listing clones for admin",
            extra={"admin_id": admin["id"], "error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Failed to list clones")


@router.get("/stats", response_model=PlatformStats)
async def get_platform_stats(
    admin: dict = Depends(get_current_admin),
    db=Depends(get_db_client)
):
    """Get overall platform statistics (admin only)."""
    try:
        users_result = await db.from_("users").select("id", count="exact").execute()
        total_users = users_result.count or 0

        clones_result = await db.from_("clones").select("id", count="exact").execute()
        total_clones = clones_result.count or 0

        convs_result = await db.from_("conversations").select("id", count="exact").execute()
        total_conversations = convs_result.count or 0

        msgs_result = await db.from_("messages").select("id", count="exact").execute()
        total_messages = msgs_result.count or 0

        docs_result = await db.from_("clone_documents").select("id", count="exact").execute()
        total_documents = docs_result.count or 0

        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        active_users_result = await db.from_("conversations").select(
            "user_id"
        ).gte("created_at", month_start.isoformat()).execute()

        unique_active_users = len(set([c["user_id"] for c in active_users_result.data])) if active_users_result.data else 0

        users_by_plan = {}
        for plan in ["FREE", "STARTER", "PRO"]:
            plan_result = await db.from_("users").select("id", count="exact").eq(
                "billing_plan", plan
            ).execute()
            users_by_plan[plan] = plan_result.count or 0

        stats = PlatformStats(
            total_users=total_users,
            total_clones=total_clones,
            total_conversations=total_conversations,
            total_messages=total_messages,
            total_documents=total_documents,
            active_users_this_month=unique_active_users,
            users_by_plan=users_by_plan
        )

        logger.info(
            "Admin retrieved platform stats",
            extra={"admin_id": admin["id"], "stats": stats.dict()}
        )

        return stats

    except Exception as e:
        logger.error(
            "Error getting platform stats",
            extra={"admin_id": admin["id"], "error": str(e)}
        )
        raise HTTPException(status_code=500, detail="Failed to get platform stats")
