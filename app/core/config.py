from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "llama3.2"
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://copilot:copilot@localhost:5432/copilot"  # type: ignore[assignment]
    )

    # RAG
    top_k: int = Field(default=8, ge=1, le=20)
    groundedness_threshold: float = Field(default=0.75, ge=0.0, le=1.0)
    max_context_tokens: int = Field(default=8000, ge=100)

    # API
    api_key: str = Field(default="change-me", repr=False)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    environment: Literal["development", "staging", "production"] = "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
