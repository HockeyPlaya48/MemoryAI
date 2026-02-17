"""Ingestion API endpoints."""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from app.ingestion.pipeline import ingest_text, ingest_pdf, ingest_url

router = APIRouter(prefix="/ingest", tags=["ingestion"])


class TextIngestRequest(BaseModel):
    text: str
    source: str = "direct_input"
    metadata: dict | None = None


class UrlIngestRequest(BaseModel):
    url: str
    metadata: dict | None = None


@router.post("/text")
async def ingest_text_endpoint(request: TextIngestRequest):
    """Ingest raw text into the knowledge base."""
    try:
        result = ingest_text(request.text, source=request.source, metadata=request.metadata)
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@router.post("/file")
async def ingest_file_endpoint(file: UploadFile = File(...)):
    """Ingest a file (PDF, TXT, MD) into the knowledge base."""
    try:
        content = await file.read()
        filename = file.filename or "upload"

        if filename.lower().endswith(".pdf"):
            result = ingest_pdf(content, filename)
        else:
            # Treat as text file
            text = content.decode("utf-8", errors="ignore")
            result = ingest_text(text, source=filename, metadata={"type": "file"})

        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")


@router.post("/url")
async def ingest_url_endpoint(request: UrlIngestRequest):
    """Ingest content from a web URL into the knowledge base."""
    try:
        result = ingest_url(request.url)
        return {"status": "success", **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
