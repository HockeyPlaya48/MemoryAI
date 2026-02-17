"""Application settings loaded from environment variables."""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM keys (optional — synthesis works without them)
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"

    # Storage
    chroma_dir: str = "./data/chroma"
    sqlite_path: str = "./data/memory.db"

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 50

    # API
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def ensure_dirs(self):
        """Create data directories if they don't exist."""
        Path(self.chroma_dir).mkdir(parents=True, exist_ok=True)
        Path(self.sqlite_path).parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()
