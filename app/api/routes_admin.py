"""Admin API endpoints for collection management."""

from fastapi import APIRouter, HTTPException

from app.indexing.vectorstore import get_collection_stats, delete_document
from app.indexing.entities import get_entity_store

router = APIRouter(tags=["admin"])


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "MemoryAI"}


@router.get("/collections")
async def list_collections():
    """List indexed documents and collection statistics."""
    try:
        vector_stats = get_collection_stats()
        entity_stats = get_entity_store().get_stats()
        return {
            "status": "success",
            **vector_stats,
            **entity_stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e}")


@router.delete("/documents/{doc_id}")
async def delete_doc(doc_id: str):
    """Delete a document and all its chunks/entities from the knowledge base."""
    try:
        chunks_deleted = delete_document(doc_id)
        get_entity_store().delete_doc_entities(doc_id)
        return {
            "status": "success",
            "doc_id": doc_id,
            "chunks_deleted": chunks_deleted,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {e}")
