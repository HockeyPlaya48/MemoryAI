"""Agent navigation: session-based threaded queries with shared memory."""

import uuid
import logging

from app.indexing.entities import get_entity_store
from app.query.engine import query as rag_query

logger = logging.getLogger(__name__)


def navigate(
    question: str,
    session_id: str | None = None,
    n_results: int = 10,
    doc_filter: str | None = None,
) -> dict:
    """Execute a session-aware query for agent navigation.

    Creates or resumes a session, retrieves with session context,
    and appends results to session memory.
    """
    entity_store = get_entity_store()

    # Create or resume session
    if not session_id:
        session_id = uuid.uuid4().hex[:12]

    entity_store.create_session(session_id)

    # Get session history for context-aware retrieval
    session_context = entity_store.get_session_context(session_id)

    # Augment query with session context if available
    augmented_query = question
    if session_context:
        # Add last query/answer for continuity
        last = session_context[-1]
        augmented_query = f"Context: Previously asked '{last['query']}'. Now: {question}"

    # Run RAG query with session context
    result = rag_query(
        augmented_query,
        n_results=n_results,
        doc_filter=doc_filter,
        session_context=session_context,
    )

    # Append to session memory
    source_names = [s["source"] for s in result.get("sources", [])]
    entity_store.append_session_context(
        session_id,
        question,
        result.get("answer", ""),
        source_names,
    )

    # Add session metadata to response
    result["session_id"] = session_id
    result["session_turns"] = len(session_context) + 1

    return result
