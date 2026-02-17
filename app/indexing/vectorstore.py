"""ChromaDB vector store operations."""

import logging

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.config import settings

logger = logging.getLogger(__name__)

_client: chromadb.ClientAPI | None = None
_collection = None

COLLECTION_NAME = "memoryai"


def get_client() -> chromadb.ClientAPI:
    """Get or initialize ChromaDB persistent client."""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        logger.info(f"ChromaDB initialized at {settings.chroma_dir}")
    return _client


def get_vectorstore():
    """Get or create the main collection."""
    global _collection
    if _collection is None:
        client = get_client()
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(f"Collection '{COLLECTION_NAME}' ready ({_collection.count()} docs)")
    return _collection


def query_vectors(
    query_embedding: list[float],
    n_results: int = 10,
    where: dict | None = None,
) -> dict:
    """Query the vector store for similar chunks."""
    collection = get_vectorstore()
    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where
    return collection.query(**kwargs)


def delete_document(doc_id: str) -> int:
    """Delete all chunks belonging to a document."""
    collection = get_vectorstore()
    results = collection.get(where={"doc_id": doc_id}, include=[])
    if results["ids"]:
        collection.delete(ids=results["ids"])
    return len(results["ids"])


def get_collection_stats() -> dict:
    """Return collection statistics."""
    collection = get_vectorstore()
    count = collection.count()
    # Get unique doc_ids
    if count > 0:
        all_meta = collection.get(include=["metadatas"])
        doc_ids = set()
        sources = set()
        for m in all_meta["metadatas"]:
            doc_ids.add(m.get("doc_id", "unknown"))
            sources.add(m.get("source", "unknown"))
        return {
            "total_chunks": count,
            "total_documents": len(doc_ids),
            "sources": list(sources),
        }
    return {"total_chunks": 0, "total_documents": 0, "sources": []}
