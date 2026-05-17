from __future__ import annotations

import json
import time
from typing import Any

import httpx
from sqlalchemy import text

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.telemetry import retrieval_latency_seconds
from app.models.api import SourceChunk
from app.storage.database import get_session_factory

logger = get_logger(__name__)


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the Ollama embeddings endpoint."""
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/embed"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            json={"model": settings.embedding_model, "input": texts},
        )
        response.raise_for_status()

    data = response.json()
    # Ollama /api/embed returns {"embeddings": [[...], [...]]}
    return data["embeddings"]


async def upsert_chunks(chunks: list[dict[str, Any]]) -> None:
    """
    Embed and upsert a list of chunk dicts into the chunks table.

    Each dict must have: id, source_type, source_id, content.
    Optional: machine_id, site, metadata (dict).
    """
    if not chunks:
        return

    # Ollama handles batches well but keep them reasonable
    batch_size = 50

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c["content"] for c in batch]
        embeddings = await embed_texts(texts)

        session_factory = get_session_factory()
        async with session_factory() as session:
            async with session.begin():
                for chunk, embedding in zip(batch, embeddings):
                    await session.execute(
                        text("""
                            INSERT INTO chunks (id, source_type, source_id, machine_id, site, content, metadata, embedding)
                            VALUES (:id, :source_type, :source_id, :machine_id, :site, :content, cast(:metadata as jsonb), cast(:embedding as vector))
                            ON CONFLICT (id) DO UPDATE SET
                                content   = EXCLUDED.content,
                                metadata  = EXCLUDED.metadata,
                                embedding = EXCLUDED.embedding
                        """),
                        {
                            "id": chunk["id"],
                            "source_type": chunk["source_type"],
                            "source_id": chunk["source_id"],
                            "machine_id": chunk.get("machine_id"),
                            "site": chunk.get("site"),
                            "content": chunk["content"],
                            "metadata": json.dumps(chunk.get("metadata", {})),
                            "embedding": str(embedding),
                        },
                    )

        logger.info("upserted_batch", offset=i, count=len(batch))


async def similarity_search(
    query: str,
    top_k: int = 5,
    filters: dict[str, Any] | None = None,
) -> list[SourceChunk]:
    """
    Embed query and retrieve top_k most similar chunks.
    Supports optional filters: machine_id, source_type, site.
    """
    t0 = time.perf_counter()

    embeddings = await embed_texts([query])
    query_vector = embeddings[0]

    where_clauses = ["1=1"]
    params: dict[str, Any] = {"query_vector": str(query_vector), "top_k": top_k}

    if filters:
        if machine_id := filters.get("machine_id"):
            where_clauses.append("machine_id = :machine_id")
            params["machine_id"] = machine_id
        if source_type := filters.get("source_type"):
            where_clauses.append("source_type = :source_type")
            params["source_type"] = source_type
        if site := filters.get("site"):
            where_clauses.append("site = :site")
            params["site"] = site

    where_sql = " AND ".join(where_clauses)

    sql = text(f"""
        SELECT
            id,
            source_type,
            source_id,
            machine_id,
            content,
            metadata,
            1 - (embedding <=> cast(:query_vector as vector)) AS score
        FROM chunks
        WHERE {where_sql}
        ORDER BY embedding <=> cast(:query_vector as vector)
        LIMIT :top_k
    """)

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(sql, params)
        rows = result.fetchall()

    latency = time.perf_counter() - t0
    retrieval_latency_seconds.observe(latency)
    logger.info("similarity_search", top_k=top_k, results=len(rows), latency_ms=round(latency * 1000, 1))

    return [
        SourceChunk(
            chunk_id=row.id,
            source_type=row.source_type,
            source_id=row.source_id,
            machine_id=row.machine_id,
            content=row.content,
            score=round(float(row.score), 4),
            metadata=row.metadata or {},
        )
        for row in rows
    ]
