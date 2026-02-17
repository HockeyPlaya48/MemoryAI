"""MemoryAI — AI-Native Data Stack API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.routes_ingest import router as ingest_router
from app.api.routes_query import router as query_router
from app.api.routes_admin import router as admin_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-load models and initialize stores on startup."""
    logger.info("MemoryAI starting up...")

    # Pre-load embedding model (warm cache)
    from app.indexing.embedder import get_embedder
    get_embedder()

    # Initialize vector store
    from app.indexing.vectorstore import get_vectorstore
    vs = get_vectorstore()
    logger.info(f"Vector store ready: {vs.count()} chunks indexed")

    # Initialize entity store
    from app.indexing.entities import get_entity_store
    es = get_entity_store()
    stats = es.get_stats()
    logger.info(f"Entity store ready: {stats['unique_entities']} entities, {stats['total_relations']} relations")

    llm_status = "Claude" if settings.anthropic_api_key else ("OpenAI" if settings.openai_api_key else "None (retrieval-only mode)")
    logger.info(f"LLM synthesis: {llm_status}")
    logger.info("MemoryAI ready!")

    yield

    logger.info("MemoryAI shutting down...")


app = FastAPI(
    title="MemoryAI",
    description="AI-native knowledge base and navigation API for agents and swarms.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all for dev, tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {
        "service": "MemoryAI",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "ingest_text": "POST /ingest/text",
            "ingest_file": "POST /ingest/file",
            "ingest_url": "POST /ingest/url",
            "query": "POST /query",
            "navigate": "POST /navigate",
            "collections": "GET /collections",
            "delete_doc": "DELETE /documents/{doc_id}",
            "health": "GET /health",
        },
    }
