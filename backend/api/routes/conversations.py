import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from backend.db.client import get_db
from backend.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    MessageResponse,
    MessageCreate,
    ChatResponse
)
from backend.api.deps import get_current_user_id, verify_clone_ownership
from backend.ai.factory import get_llm_provider

logger = logging.getLogger(__name__)
logger.info("CONVERSATIONS_ROUTES_LOADED", extra={"file": __file__})

router = APIRouter()


@router.get("", response_model=List[ConversationResponse])
async def list_conversations(
    clone_id: str,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Get all conversations for a clone."""

    logger.info("LIST_CONVERSATIONS_REQUEST", extra={
        "clone_id": clone_id,
        "user_id": user_id
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    result = db.table("conversations").select("*").eq("clone_id", clone_id).order("created_at", desc=True).execute()

    logger.info("LIST_CONVERSATIONS_SUCCESS", extra={
        "clone_id": clone_id,
        "conversation_count": len(result.data)
    })

    return [ConversationResponse(**conv) for conv in result.data]


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    clone_id: str,
    conversation_data: ConversationCreate,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Create a new conversation with a clone."""

    logger.info("CREATE_CONVERSATION_REQUEST", extra={
        "clone_id": clone_id,
        "user_id": user_id
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    conversation_insert = {
        "user_id": user_id,
        "clone_id": clone_id,
        "title": conversation_data.title
    }

    result = db.table("conversations").insert(conversation_insert).execute()

    if not result.data:
        logger.error("CONVERSATION_CREATION_FAILED", extra={
            "clone_id": clone_id,
            "user_id": user_id
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create conversation"
        )

    conversation = result.data[0]

    logger.info("CONVERSATION_CREATED_SUCCESS", extra={
        "conversation_id": conversation["id"],
        "clone_id": clone_id
    })

    return ConversationResponse(**conversation)


@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def list_messages(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Get all messages in a conversation."""

    logger.info("LIST_MESSAGES_REQUEST", extra={
        "conversation_id": conversation_id,
        "user_id": user_id
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    conv_result = db.table("conversations").select("*").eq("id", conversation_id).eq("user_id", user_id).maybe_single().execute()

    if not conv_result.data:
        logger.warning("CONVERSATION_NOT_FOUND", extra={
            "conversation_id": conversation_id,
            "user_id": user_id
        })
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    result = db.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()

    logger.info("LIST_MESSAGES_SUCCESS", extra={
        "conversation_id": conversation_id,
        "message_count": len(result.data)
    })

    return [MessageResponse(**msg) for msg in result.data]


@router.post("/{conversation_id}/messages", response_model=ChatResponse)
async def send_message(
    conversation_id: str,
    message_data: MessageCreate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Send a message and get AI clone response."""

    logger.info("SEND_MESSAGE_REQUEST", extra={
        "conversation_id": conversation_id,
        "user_id": user_id,
        "message_length": len(message_data.content)
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    conv_result = db.table("conversations").select("*, clones(*)").eq("id", conversation_id).eq("user_id", user_id).maybe_single().execute()

    if not conv_result.data:
        logger.warning("CONVERSATION_NOT_FOUND_FOR_MESSAGE", extra={
            "conversation_id": conversation_id
        })
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    conversation = conv_result.data
    clone = conversation["clones"]

    user_message_insert = {
        "conversation_id": conversation_id,
        "role": "user",
        "content": message_data.content
    }

    user_msg_result = db.table("messages").insert(user_message_insert).execute()

    if not user_msg_result.data:
        logger.error("USER_MESSAGE_CREATION_FAILED", extra={
            "conversation_id": conversation_id
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create message"
        )

    user_message = user_msg_result.data[0]

    logger.info("USER_MESSAGE_SAVED", extra={
        "message_id": user_message["id"],
        "conversation_id": conversation_id
    })

    messages_result = db.table("messages").select("*").eq("conversation_id", conversation_id).order("created_at").execute()

    conversation_history = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in messages_result.data[:-1]
    ]

    memories_result = db.table("memories").select("*").eq("clone_id", clone["id"]).limit(10).execute()

    memories = [
        {
            "title": mem["title"],
            "content": mem["content"]
        }
        for mem in memories_result.data
    ]

    logger.info("GENERATING_CLONE_RESPONSE", extra={
        "clone_id": clone["id"],
        "clone_name": clone["name"],
        "memories_count": len(memories),
        "history_length": len(conversation_history)
    })

    llm_provider = get_llm_provider()

    try:
        clone_reply = await llm_provider.generate_clone_reply(
            clone_info={
                "id": clone["id"],
                "name": clone["name"],
                "description": clone["description"]
            },
            memories=memories,
            conversation_history=conversation_history,
            user_message=message_data.content,
            tone_config=clone["tone_config"]
        )

        logger.info("CLONE_RESPONSE_GENERATED", extra={
            "clone_id": clone["id"],
            "response_length": len(clone_reply)
        })

    except Exception as e:
        logger.error("CLONE_RESPONSE_GENERATION_ERROR", extra={
            "error": str(e),
            "clone_id": clone["id"]
        }, exc_info=True)

        clone_reply = "I'm having trouble expressing myself right now. Can we try again?"

    clone_message_insert = {
        "conversation_id": conversation_id,
        "role": "clone",
        "content": clone_reply
    }

    clone_msg_result = db.table("messages").insert(clone_message_insert).execute()

    if not clone_msg_result.data:
        logger.error("CLONE_MESSAGE_CREATION_FAILED", extra={
            "conversation_id": conversation_id
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create clone message"
        )

    clone_message = clone_msg_result.data[0]

    logger.info("CHAT_EXCHANGE_COMPLETE", extra={
        "conversation_id": conversation_id,
        "user_message_id": user_message["id"],
        "clone_message_id": clone_message["id"]
    })

    return ChatResponse(
        user_message=MessageResponse(**user_message),
        clone_message=MessageResponse(**clone_message)
    )
