from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            str(settings.database_url),
            pool_size=5,
            max_overflow=10,
            echo=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def init_db() -> None:
    """Create the pgvector extension and the chunks table if they don't exist."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chunks (
                id          TEXT PRIMARY KEY,
                source_type TEXT NOT NULL,
                source_id   TEXT NOT NULL,
                machine_id  TEXT,
                site        TEXT,
                content     TEXT NOT NULL,
                metadata    JSONB NOT NULL DEFAULT '{}',
                embedding   vector(768),
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS chunks_embedding_idx
            ON chunks USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 50)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS chunks_machine_id_idx ON chunks (machine_id)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS chunks_source_type_idx ON chunks (source_type)
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS feedback (
                id              TEXT PRIMARY KEY,
                question_id     TEXT NOT NULL,
                answer_id       TEXT NOT NULL,
                question        TEXT NOT NULL,
                answer          TEXT NOT NULL,
                rating          TEXT NOT NULL,
                comment         TEXT NOT NULL DEFAULT '',
                correct_source_id TEXT,
                reviewer_id     TEXT,
                promoted        BOOLEAN NOT NULL DEFAULT false,
                submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS feedback_rating_idx ON feedback (rating)
        """))
        await conn.execute(text("""
            CREATE INDEX IF NOT EXISTS feedback_promoted_idx ON feedback (promoted)
        """))
    logger.info("db_init_complete")
