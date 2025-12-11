import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from supabase import Client

from backend.db.client import get_db
from backend.schemas.document import DocumentCreate, DocumentResponse, DocumentWithStats
from backend.api.deps import get_current_user_id, verify_clone_ownership, get_current_user
from backend.services.rag_service import RAGService
from backend.services.quota_service import check_document_quota

logger = logging.getLogger(__name__)
logger.info("DOCUMENTS_ROUTES_LOADED", extra={"file": __file__})

router = APIRouter()


@router.get("", response_model=List[DocumentWithStats])
async def list_documents(
    clone_id: str,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Get all documents for a clone with chunk counts."""

    logger.info("LIST_DOCUMENTS_REQUEST", extra={
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

    result = db.table("clone_documents").select("*").eq("clone_id", clone_id).order("created_at", desc=True).execute()

    documents_with_stats = []
    for doc in result.data:
        chunk_count_result = db.table("clone_document_chunks").select("id", count="exact").eq("document_id", doc["id"]).execute()
        chunk_count = chunk_count_result.count if chunk_count_result.count is not None else 0

        documents_with_stats.append(DocumentWithStats(
            **doc,
            chunk_count=chunk_count
        ))

    logger.info("LIST_DOCUMENTS_SUCCESS", extra={
        "clone_id": clone_id,
        "document_count": len(documents_with_stats)
    })

    return documents_with_stats


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    clone_id: str,
    document_data: DocumentCreate,
    current_user: dict = Depends(get_current_user),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Create a new document and ingest it for RAG."""

    user_id = current_user["id"]
    billing_plan = current_user.get("billing_plan", "FREE")

    logger.info("CREATE_DOCUMENT_REQUEST", extra={
        "clone_id": clone_id,
        "user_id": user_id,
        "title": document_data.title,
        "content_length": len(document_data.content),
        "billing_plan": billing_plan
    })

    is_allowed, error_message = await check_document_quota(
        db, clone_id, user_id, billing_plan
    )

    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=error_message
        )

    rag_service = RAGService(db)

    embedding_provider = clone.get("embedding_provider") or "dummy"

    try:
        document_id = await rag_service.ingest_clone_document(
            clone_id=clone_id,
            user_id=user_id,
            title=document_data.title,
            content=document_data.content,
            source_type=document_data.source_type,
            embedding_provider=embedding_provider
        )

        doc_result = db.table("clone_documents").select("*").eq("id", document_id).maybe_single().execute()

        if not doc_result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created document"
            )

        logger.info("CREATE_DOCUMENT_SUCCESS", extra={
            "document_id": document_id,
            "clone_id": clone_id
        })

        return DocumentResponse(**doc_result.data)

    except Exception as e:
        logger.error("CREATE_DOCUMENT_FAILED", extra={
            "clone_id": clone_id,
            "error": str(e)
        }, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create document: {str(e)}"
        )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    clone_id: str,
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    clone: dict = Depends(verify_clone_ownership),
    db: Client = Depends(get_db)
):
    """Delete a document and its chunks."""

    logger.info("DELETE_DOCUMENT_REQUEST", extra={
        "document_id": document_id,
        "clone_id": clone_id
    })

    try:
        db.rpc('set_config', {
            'setting': 'app.current_user_id',
            'value': user_id,
            'is_local': True
        }).execute()
    except Exception:
        pass

    db.table("clone_documents").delete().eq("id", document_id).eq("clone_id", clone_id).execute()

    logger.info("DELETE_DOCUMENT_SUCCESS", extra={
        "document_id": document_id
    })

    return None
