"""RAG query engine: retrieve → rank → synthesize."""

import logging

from app.indexing.embedder import embed_query
from app.indexing.vectorstore import query_vectors
from app.indexing.entities import get_entity_store
from app.query.synthesizer import synthesize

logger = logging.getLogger(__name__)


def query(
    question: str,
    n_results: int = 10,
    doc_filter: str | None = None,
    session_context: list[dict] | None = None,
) -> dict:
    """Execute a RAG query against the knowledge base.

    Returns structured response with answer, sources, and entity connections.
    """
    if not question or not question.strip():
        return {"answer": "Please provide a question.", "sources": [], "connections": []}

    # 1. Embed the query
    q_embedding = embed_query(question)

    # 2. Vector similarity search
    where = {"doc_id": doc_filter} if doc_filter else None
    results = query_vectors(q_embedding, n_results=n_results, where=where)

    # 3. Parse results into structured chunks
    chunks = []
    if results and results.get("documents") and results["documents"][0]:
        for i in range(len(results["documents"][0])):
            doc_text = results["documents"][0][i]
            metadata = results["metadatas"][0][i] if results["metadatas"] else {}
            distance = results["distances"][0][i] if results["distances"] else 0
            # Convert cosine distance to similarity score (ChromaDB returns distance)
            score = round(1 - distance, 4)

            chunks.append({
                "text": doc_text,
                "source": metadata.get("source", "unknown"),
                "doc_id": metadata.get("doc_id", ""),
                "chunk_index": metadata.get("chunk_index", 0),
                "score": score,
            })

    # 4. Find entity connections
    connections = _find_connections(question, chunks)

    # 5. Synthesize answer
    answer = synthesize(question, chunks, session_context)

    # 6. Build response
    sources = [
        {
            "text": c["text"][:500],
            "source": c["source"],
            "relevance_score": c["score"],
        }
        for c in chunks[:5]
    ]

    return {
        "answer": answer,
        "sources": sources,
        "connections": connections,
        "total_chunks_retrieved": len(chunks),
    }


def _find_connections(question: str, chunks: list[dict]) -> list[dict]:
    """Find entity-based connections across retrieved chunks."""
    entity_store = get_entity_store()
    connections = []
    seen_entities = set()

    for chunk in chunks[:5]:
        doc_id = chunk.get("doc_id", "")
        if not doc_id:
            continue

        entities = entity_store.get_entities_for_doc(doc_id)
        for ent in entities[:5]:
            name = ent["name"]
            if name in seen_entities:
                continue
            seen_entities.add(name)

            related = entity_store.find_related_entities(name, limit=3)
            if related:
                connections.append({
                    "entity": name,
                    "type": ent["type"],
                    "related": [r["entity"] for r in related],
                })

    return connections[:10]
