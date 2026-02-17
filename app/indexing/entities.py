"""Lightweight entity extraction and SQLite graph storage."""

import re
import sqlite3
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_store = None


class EntityStore:
    """SQLite-backed entity and relation store."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL,
                UNIQUE(name, chunk_id)
            );
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_a TEXT NOT NULL,
                entity_b TEXT NOT NULL,
                relation_type TEXT DEFAULT 'co_occurs',
                doc_id TEXT NOT NULL,
                chunk_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                last_query TEXT,
                context TEXT DEFAULT '[]'
            );
            CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
            CREATE INDEX IF NOT EXISTS idx_entities_doc ON entities(doc_id);
            CREATE INDEX IF NOT EXISTS idx_relations_entity ON relations(entity_a);
        """)
        self.conn.commit()

    def extract_and_store(self, doc_id: str, chunks: list[str], chunk_ids: list[str]):
        """Extract entities from chunks and store with relations."""
        for chunk_text, chunk_id in zip(chunks, chunk_ids):
            entities = self._extract_entities(chunk_text)

            for name, etype in entities:
                try:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO entities (name, entity_type, doc_id, chunk_id) VALUES (?, ?, ?, ?)",
                        (name, etype, doc_id, chunk_id),
                    )
                except sqlite3.Error:
                    pass

            # Create co-occurrence relations between entities in the same chunk
            entity_names = [name for name, _ in entities]
            for i in range(len(entity_names)):
                for j in range(i + 1, len(entity_names)):
                    try:
                        self.conn.execute(
                            "INSERT INTO relations (entity_a, entity_b, relation_type, doc_id, chunk_id) VALUES (?, ?, 'co_occurs', ?, ?)",
                            (entity_names[i], entity_names[j], doc_id, chunk_id),
                        )
                    except sqlite3.Error:
                        pass

        self.conn.commit()

    def _extract_entities(self, text: str) -> list[tuple[str, str]]:
        """Extract entities using regex heuristics (no spaCy dependency)."""
        entities = []

        # Capitalized multi-word phrases (likely proper nouns)
        for match in re.finditer(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b", text):
            entities.append((match.group(0), "proper_noun"))

        # $TICKERS
        for match in re.finditer(r"\$([A-Z]{2,10})\b", text):
            entities.append((f"${match.group(1)}", "ticker"))

        # @mentions
        for match in re.finditer(r"@(\w{2,30})\b", text):
            entities.append((f"@{match.group(1)}", "mention"))

        # URLs
        for match in re.finditer(r"https?://[^\s<>\"]+", text):
            entities.append((match.group(0), "url"))

        # Email addresses
        for match in re.finditer(r"[\w.+-]+@[\w-]+\.[\w.-]+", text):
            entities.append((match.group(0), "email"))

        # Percentages and dollar amounts
        for match in re.finditer(r"\$[\d,.]+[KMBkmb]?|\d+\.?\d*%", text):
            entities.append((match.group(0), "metric"))

        return list(set(entities))

    def find_connected_chunks(self, entity_name: str, limit: int = 10) -> list[str]:
        """Find chunk_ids connected to an entity."""
        cursor = self.conn.execute(
            "SELECT DISTINCT chunk_id FROM entities WHERE name = ? LIMIT ?",
            (entity_name, limit),
        )
        return [row[0] for row in cursor.fetchall()]

    def find_related_entities(self, entity_name: str, limit: int = 10) -> list[dict]:
        """Find entities related to the given entity via co-occurrence."""
        cursor = self.conn.execute(
            """
            SELECT DISTINCT entity_b AS related, relation_type, chunk_id
            FROM relations WHERE entity_a = ?
            UNION
            SELECT DISTINCT entity_a AS related, relation_type, chunk_id
            FROM relations WHERE entity_b = ?
            LIMIT ?
            """,
            (entity_name, entity_name, limit),
        )
        return [{"entity": row[0], "relation": row[1], "chunk_id": row[2]} for row in cursor.fetchall()]

    def get_entities_for_doc(self, doc_id: str) -> list[dict]:
        """Get all entities extracted from a document."""
        cursor = self.conn.execute(
            "SELECT DISTINCT name, entity_type FROM entities WHERE doc_id = ?",
            (doc_id,),
        )
        return [{"name": row[0], "type": row[1]} for row in cursor.fetchall()]

    def delete_doc_entities(self, doc_id: str):
        """Delete all entities and relations for a document."""
        self.conn.execute("DELETE FROM entities WHERE doc_id = ?", (doc_id,))
        self.conn.execute("DELETE FROM relations WHERE doc_id = ?", (doc_id,))
        self.conn.commit()

    def get_stats(self) -> dict:
        """Return entity store statistics."""
        entities = self.conn.execute("SELECT COUNT(DISTINCT name) FROM entities").fetchone()[0]
        relations = self.conn.execute("SELECT COUNT(*) FROM relations").fetchone()[0]
        return {"unique_entities": entities, "total_relations": relations}

    # ── Session management for agent navigation ──

    def create_session(self, session_id: str):
        from datetime import datetime, timezone
        self.conn.execute(
            "INSERT OR IGNORE INTO sessions (id, created_at, context) VALUES (?, ?, '[]')",
            (session_id, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()

    def get_session_context(self, session_id: str) -> list[dict]:
        import json
        cursor = self.conn.execute("SELECT context FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
        return []

    def append_session_context(self, session_id: str, query: str, answer: str, sources: list):
        import json
        context = self.get_session_context(session_id)
        context.append({"query": query, "answer": answer[:500], "sources": [s[:100] for s in sources[:3]]})
        # Keep last 20 turns
        context = context[-20:]
        self.conn.execute(
            "UPDATE sessions SET context = ?, last_query = ? WHERE id = ?",
            (json.dumps(context), query, session_id),
        )
        self.conn.commit()


def get_entity_store() -> EntityStore:
    """Get or initialize the entity store singleton."""
    global _store
    if _store is None:
        _store = EntityStore(settings.sqlite_path)
        logger.info(f"Entity store initialized at {settings.sqlite_path}")
    return _store
