# MemoryAI — AI-Native Data Stack

A lightweight, agent-focused knowledge base and navigation tool. Ingest messy data (text, PDFs, URLs), automatically organize and index it, then let AI agents query it for structured, cited, context-rich responses.

## Features

- **Universal Ingestion** — Drop in text, PDFs, or web URLs. Auto-chunks, embeds, and indexes.
- **Vector Search** — ChromaDB with HuggingFace embeddings (all-MiniLM-L6-v2, runs locally, no API key).
- **Entity Graph** — Automatic entity extraction with co-occurrence relations stored in SQLite.
- **RAG Query Engine** — Retrieval + optional LLM synthesis (Claude or OpenAI). Works without API keys in retrieval-only mode.
- **Agent Navigation** — Session-based threaded queries. Multiple agents can run parallel sessions against the same knowledge base.
- **Structured Outputs** — Every response includes answer, cited sources with relevance scores, and entity connections.

## Quick Start

```bash
# Clone and install
git clone https://github.com/HockeyPlaya48/MemoryAI.git
cd MemoryAI
pip install -r requirements.txt

# Optional: add LLM key for synthesis (works without it)
cp .env.example .env
# Edit .env and add ANTHROPIC_API_KEY or OPENAI_API_KEY

# Start the API
uvicorn app.main:app --reload

# In a separate terminal, start the demo UI
streamlit run demo.py
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/ingest/text` | Ingest raw text |
| `POST` | `/ingest/file` | Ingest PDF/TXT/MD file upload |
| `POST` | `/ingest/url` | Ingest content from a web URL |
| `POST` | `/query` | Natural language query with sources |
| `POST` | `/navigate` | Session-aware agent query (threaded) |
| `GET` | `/collections` | List documents + stats |
| `DELETE` | `/documents/{doc_id}` | Remove document from index |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API documentation |

## Example Usage

```bash
# Ingest some text
curl -X POST http://localhost:8000/ingest/text \
  -H "Content-Type: application/json" \
  -d '{"text": "Bitcoin reached $100k in 2025. Ethereum shifted to proof of stake.", "source": "crypto_notes"}'

# Query
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "What happened with Bitcoin?"}'

# Agent navigation (threaded session)
curl -X POST http://localhost:8000/navigate \
  -H "Content-Type: application/json" \
  -d '{"question": "Tell me about crypto trends", "session_id": "agent-001"}'
```

## Architecture

```
app/
├── main.py          — FastAPI entrypoint
├── config.py        — Settings from .env
├── ingestion/       — Text/PDF/URL extraction and chunking
├── indexing/        — Embeddings (HuggingFace), ChromaDB, entity graph (SQLite)
├── query/           — RAG engine, LLM synthesis, agent navigation
└── api/             — REST endpoints
```

## Tech Stack

- **FastAPI** — Async API with auto-generated OpenAPI docs
- **ChromaDB** — Embedded vector database (no server needed)
- **sentence-transformers** — Free local embeddings (all-MiniLM-L6-v2)
- **SQLite** — Entity graph + session storage (zero config)
- **Streamlit** — Demo UI

## Scaling Notes

- Swap ChromaDB → Pinecone/Weaviate for cloud scale
- Add spaCy NER for richer entity extraction
- Add cross-encoder reranking for better retrieval
- WebSocket endpoint for streaming responses
- API key auth for multi-tenant agent access
