"""Unified ingestion pipeline: text/PDF/URL → chunks → indexed."""

import hashlib
import logging
from datetime import datetime, timezone

from app.config import settings
from app.ingestion.chunker import chunk_text
from app.ingestion.extractors import extract_pdf, extract_url
from app.indexing.embedder import get_embedder
from app.indexing.vectorstore import get_vectorstore
from app.indexing.entities import get_entity_store

logger = logging.getLogger(__name__)


def generate_doc_id(source: str, content_prefix: str) -> str:
    """Generate deterministic document ID from source + content."""
    raw = f"{source}:{content_prefix[:200]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def ingest_text(text: str, source: str = "direct_input", metadata: dict | None = None) -> dict:
    """Ingest raw text: chunk, embed, index, extract entities."""
    if not text or not text.strip():
        raise ValueError("Empty text provided")

    doc_id = generate_doc_id(source, text)
    timestamp = datetime.now(timezone.utc).isoformat()

    # Chunk
    chunks = chunk_text(text, settings.chunk_size, settings.chunk_overlap)
    if not chunks:
        raise ValueError("Text produced no chunks after splitting")

    # Embed
    embedder = get_embedder()
    embeddings = embedder.encode(chunks)

    # Store in vector DB
    vs = get_vectorstore()
    chunk_ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "doc_id": doc_id,
            "source": source,
            "chunk_index": i,
            "timestamp": timestamp,
            **(metadata or {}),
        }
        for i in range(len(chunks))
    ]
    vs.add(
        ids=chunk_ids,
        embeddings=[e.tolist() for e in embeddings],
        documents=chunks,
        metadatas=metadatas,
    )

    # Extract entities and link to chunks
    entity_store = get_entity_store()
    entity_store.extract_and_store(doc_id, chunks, chunk_ids)

    logger.info(f"Ingested doc_id={doc_id} source={source} chunks={len(chunks)}")

    return {
        "doc_id": doc_id,
        "source": source,
        "chunks_created": len(chunks),
        "timestamp": timestamp,
    }


def ingest_pdf(file_bytes: bytes, filename: str = "upload.pdf") -> dict:
    """Ingest a PDF file."""
    text = extract_pdf(file_bytes)
    if not text.strip():
        raise ValueError("PDF contained no extractable text")
    return ingest_text(text, source=filename, metadata={"type": "pdf"})


def ingest_url(url: str) -> dict:
    """Ingest content from a web URL."""
    text = extract_url(url)
    if not text.strip():
        raise ValueError(f"No text extracted from {url}")
    return ingest_text(text, source=url, metadata={"type": "web"})
