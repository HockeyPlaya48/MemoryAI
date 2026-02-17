"""Query and navigation API endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.query.engine import query as rag_query
from app.query.navigator import navigate

router = APIRouter(tags=["query"])


class QueryRequest(BaseModel):
    question: str
    n_results: int = 10
    doc_filter: str | None = None


class NavigateRequest(BaseModel):
    question: str
    session_id: str | None = None
    n_results: int = 10
    doc_filter: str | None = None


@router.post("/query")
async def query_endpoint(request: QueryRequest):
    """Query the knowledge base with natural language.

    Returns structured response with answer, cited sources, and entity connections.
    """
    try:
        result = rag_query(
            request.question,
            n_results=request.n_results,
            doc_filter=request.doc_filter,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")


@router.post("/navigate")
async def navigate_endpoint(request: NavigateRequest):
    """Session-aware agent navigation endpoint.

    Maintains conversation context across queries. Pass session_id
    to continue a thread, or omit to start a new session.
    Multiple agents can run parallel sessions against the same knowledge base.
    """
    try:
        result = navigate(
            request.question,
            session_id=request.session_id,
            n_results=request.n_results,
            doc_filter=request.doc_filter,
        )
        return {"status": "success", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Navigation failed: {e}")
