import logging
from typing import List
from uuid import UUID
from supabase import Client

from backend.providers.embeddings.factory import get_embedding_provider

logger = logging.getLogger(__name__)
logger.info("RAG_SERVICE_LOADED", extra={"file": __file__})


class RAGService:
    """Service for RAG (Retrieval-Augmented Generation) operations."""

    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 100

    def __init__(self, db: Client):
        self.db = db

    async def ingest_clone_document(
        self,
        clone_id: UUID,
        user_id: UUID,
        title: str,
        content: str,
        source_type: str = "manual",
        embedding_provider: str = "dummy"
    ) -> str:
        """
        Ingest a document for a clone: store it, chunk it, and generate embeddings.

        Args:
            clone_id: Clone ID
            user_id: User ID (owner)
            title: Document title
            content: Document content
            source_type: Source type (e.g., "manual", "upload")
            embedding_provider: Provider to use for embeddings

        Returns:
            Document ID
        """
        logger.info("RAG_INGEST_DOCUMENT_START", extra={
            "clone_id": str(clone_id),
            "user_id": str(user_id),
            "title": title,
            "content_length": len(content)
        })

        try:
            self.db.rpc('set_config', {
                'setting': 'app.current_user_id',
                'value': str(user_id),
                'is_local': True
            }).execute()
        except Exception:
            pass

        doc_insert = {
            "clone_id": str(clone_id),
            "user_id": str(user_id),
            "title": title,
            "content": content,
            "source_type": source_type
        }

        doc_result = self.db.table("clone_documents").insert(doc_insert).execute()

        if not doc_result.data:
            logger.error("RAG_INGEST_DOCUMENT_FAILED")
            raise Exception("Failed to create document")

        document = doc_result.data[0]
        document_id = document["id"]

        logger.info("RAG_DOCUMENT_CREATED", extra={
            "document_id": document_id
        })

        chunks = self._chunk_text(content)

        logger.info("RAG_TEXT_CHUNKED", extra={
            "chunk_count": len(chunks)
        })

        provider = get_embedding_provider(embedding_provider)
        embeddings = await provider.embed(chunks)

        logger.info("RAG_EMBEDDINGS_GENERATED", extra={
            "embedding_count": len(embeddings),
            "dimension": len(embeddings[0]) if embeddings else 0
        })

        chunk_inserts = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_inserts.append({
                "clone_id": str(clone_id),
                "document_id": document_id,
                "chunk_index": idx,
                "content": chunk,
                "embedding": embedding
            })

        if chunk_inserts:
            self.db.table("clone_document_chunks").insert(chunk_inserts).execute()

        logger.info("RAG_INGEST_DOCUMENT_COMPLETE", extra={
            "document_id": document_id,
            "chunks_stored": len(chunk_inserts)
        })

        return document_id

    async def retrieve_relevant_context(
        self,
        clone_id: UUID,
        user_id: UUID,
        query: str,
        limit: int = 5,
        embedding_provider: str = "dummy"
    ) -> List[str]:
        """
        Retrieve relevant text chunks for a query using semantic similarity.

        Args:
            clone_id: Clone ID
            user_id: User ID (for RLS)
            query: Query text
            limit: Maximum number of chunks to return
            embedding_provider: Provider to use for embeddings

        Returns:
            List of relevant text chunks
        """
        logger.info("RAG_RETRIEVE_START", extra={
            "clone_id": str(clone_id),
            "query_length": len(query),
            "limit": limit
        })

        try:
            self.db.rpc('set_config', {
                'setting': 'app.current_user_id',
                'value': str(user_id),
                'is_local': True
            }).execute()
        except Exception:
            pass

        chunks_result = self.db.table("clone_document_chunks")\
            .select("content, embedding")\
            .eq("clone_id", str(clone_id))\
            .execute()

        if not chunks_result.data:
            logger.info("RAG_NO_CHUNKS_FOUND")
            return []

        logger.info("RAG_CHUNKS_LOADED", extra={
            "chunk_count": len(chunks_result.data)
        })

        provider = get_embedding_provider(embedding_provider)
        query_embedding = (await provider.embed([query]))[0]

        scored_chunks = []
        for chunk_data in chunks_result.data:
            chunk_embedding = chunk_data["embedding"]
            if not chunk_embedding:
                continue

            similarity = self._cosine_similarity(query_embedding, chunk_embedding)
            scored_chunks.append((similarity, chunk_data["content"]))

        scored_chunks.sort(reverse=True, key=lambda x: x[0])

        top_chunks = [content for _, content in scored_chunks[:limit]]

        logger.info("RAG_RETRIEVE_COMPLETE", extra={
            "retrieved_chunks": len(top_chunks),
            "top_score": scored_chunks[0][0] if scored_chunks else 0
        })

        return top_chunks

    def _chunk_text(self, text: str) -> List[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: Text to chunk

        Returns:
            List of text chunks
        """
        words = text.split()
        chunks = []

        start = 0
        while start < len(words):
            end = start + self.CHUNK_SIZE
            chunk_words = words[start:end]
            chunks.append(" ".join(chunk_words))

            start = end - self.CHUNK_OVERLAP
            if start >= len(words):
                break

        return chunks if chunks else [text]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity score (0-1)
        """
        if len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)
