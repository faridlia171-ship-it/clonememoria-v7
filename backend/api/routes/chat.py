import logging
import json
import base64
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from supabase import Client

from backend.db.client import get_db
from backend.schemas.conversation import MessageCreate, ChatResponse
from backend.schemas.ai_config import TTSRequest
from backend.api.deps import get_current_user_id
from backend.providers.llm.factory import get_llm_provider
from backend.providers.tts.factory import get_tts_provider
from backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)
logger.info("CHAT_ROUTES_LOADED", extra={"file": __file__})

router = APIRouter()


@router.post("/{clone_id}/stream")
async def stream_chat(
    clone_id: str,
    message_data: MessageCreate,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Stream chat response using Server-Sent Events."""

    logger.info("STREAM_CHAT_REQUEST", extra={
        "clone_id": clone_id,
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

    clone_result = db.table("clones").select("*").eq("id", clone_id).eq("user_id", user_id).maybe_single().execute()

    if not clone_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clone not found"
        )

    clone = clone_result.data

    conversations = db.table("conversations").select("*").eq("clone_id", clone_id).order("created_at", desc=True).limit(1).execute()

    if conversations.data:
        conversation_id = conversations.data[0]["id"]
    else:
        conv_insert = {
            "user_id": user_id,
            "clone_id": clone_id,
            "title": f"Chat with {clone['name']}"
        }
        conv_result = db.table("conversations").insert(conv_insert).execute()
        conversation_id = conv_result.data[0]["id"]

    async def generate_stream():
        try:
            rag_service = RAGService(db)

            embedding_provider = clone.get("embedding_provider") or "dummy"
            rag_context = await rag_service.retrieve_relevant_context(
                clone_id=clone_id,
                user_id=user_id,
                query=message_data.content,
                limit=3,
                embedding_provider=embedding_provider
            )

            memories_result = db.table("memories").select("title, content").eq("clone_id", clone_id).limit(5).execute()
            memories = memories_result.data

            system_prompt = f"""You are {clone['name']}. {clone['description']}

Your personality traits:
- Warmth: {clone['tone_config'].get('warmth', 0.7)}
- Humor: {clone['tone_config'].get('humor', 0.5)}
- Formality: {clone['tone_config'].get('formality', 0.3)}

Key memories:
{chr(10).join(f"- {m['title']}: {m['content'][:100]}" for m in memories[:3]) if memories else 'No memories yet'}

Relevant knowledge:
{chr(10).join(f"- {ctx[:150]}" for ctx in rag_context[:2]) if rag_context else 'No additional context'}

Respond naturally as this person would, drawing from memories and knowledge."""

            messages_result = db.table("messages").select("role, content").eq("conversation_id", conversation_id).order("created_at").limit(10).execute()

            history = [{"role": msg["role"], "content": msg["content"]} for msg in messages_result.data]

            llm_provider_name = clone.get("llm_provider") or "dummy"
            llm_model = clone.get("llm_model")
            temperature = float(clone.get("temperature", 0.7))
            max_tokens = clone.get("max_tokens")

            provider = get_llm_provider(llm_provider_name, llm_model)

            collected_response = []

            async for chunk in provider.stream(
                prompt=message_data.content,
                system=system_prompt,
                messages=history,
                temperature=temperature,
                max_tokens=max_tokens
            ):
                collected_response.append(chunk)
                yield f"data: {json.dumps({'token': chunk, 'done': False})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

            full_response = "".join(collected_response)

            user_msg_insert = {
                "conversation_id": conversation_id,
                "role": "user",
                "content": message_data.content
            }
            db.table("messages").insert(user_msg_insert).execute()

            clone_msg_insert = {
                "conversation_id": conversation_id,
                "role": "clone",
                "content": full_response
            }
            db.table("messages").insert(clone_msg_insert).execute()

            logger.info("STREAM_CHAT_COMPLETE", extra={
                "clone_id": clone_id,
                "response_length": len(full_response)
            })

        except Exception as e:
            logger.error("STREAM_CHAT_ERROR", extra={
                "clone_id": clone_id,
                "error": str(e)
            }, exc_info=True)
            yield f"data: {json.dumps({'error': str(e), 'done': True})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@router.post("/tts/{clone_id}")
async def synthesize_speech(
    clone_id: str,
    tts_data: TTSRequest,
    user_id: str = Depends(get_current_user_id),
    db: Client = Depends(get_db)
):
    """Synthesize speech from text using clone's TTS settings."""

    logger.info("TTS_SYNTHESIZE_REQUEST", extra={
        "clone_id": clone_id,
        "user_id": user_id,
        "text_length": len(tts_data.text)
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    clone_result = db.table("clones").select("*").eq("id", clone_id).eq("user_id", user_id).maybe_single().execute()

    if not clone_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clone not found"
        )

    clone = clone_result.data

    tts_provider_name = clone.get("tts_provider") or "dummy"
    voice_id = clone.get("tts_voice_id")

    provider = get_tts_provider(tts_provider_name)

    try:
        audio_bytes = await provider.synthesize(
            text=tts_data.text,
            voice_id=voice_id
        )

        audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')

        logger.info("TTS_SYNTHESIZE_COMPLETE", extra={
            "clone_id": clone_id,
            "audio_size": len(audio_bytes)
        })

        return {
            "audio_base64": audio_base64,
            "format": "wav"
        }

    except Exception as e:
        logger.error("TTS_SYNTHESIZE_ERROR", extra={
            "clone_id": clone_id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"TTS synthesis failed: {str(e)}"
        )
