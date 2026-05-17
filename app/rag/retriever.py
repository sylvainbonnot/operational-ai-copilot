from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.api import AskRequest, SourceChunk
from app.storage.vector_store import similarity_search

logger = get_logger(__name__)


async def retrieve(request: AskRequest) -> list[SourceChunk]:
    """
    Retrieve relevant chunks for a question.

    Strategy:
    - Always run a broad unscoped search (catches manuals, which have machine_id=NULL).
    - When machine_id is provided, also run a machine-scoped search and merge results,
      deduplicating by chunk_id and re-ranking by score.
    - This ensures machine-specific tickets/notes AND general manuals both surface.
    """
    settings = get_settings()
    top_k = request.top_k or settings.top_k

    extra_filters: dict[str, Any] = (
        {k: v for k, v in request.filters.items() if k != "machine_id"} if request.filters else {}
    )

    # Always fetch unscoped results (picks up manuals with machine_id=NULL)
    unscoped = await similarity_search(
        query=request.question,
        top_k=top_k,
        filters=extra_filters or None,
    )

    if not request.machine_id:
        logger.info("retrieved_chunks", count=len(unscoped), machine_id=None)
        return unscoped

    # Also fetch machine-scoped results and merge
    scoped_filters = {"machine_id": request.machine_id, **extra_filters}
    scoped = await similarity_search(
        query=request.question,
        top_k=top_k,
        filters=scoped_filters,
    )

    # Merge: deduplicate by chunk_id, keep highest score, re-rank
    seen: dict[str, SourceChunk] = {}
    for chunk in scoped + unscoped:
        if chunk.chunk_id not in seen or chunk.score > seen[chunk.chunk_id].score:
            seen[chunk.chunk_id] = chunk

    merged = sorted(seen.values(), key=lambda c: c.score, reverse=True)[:top_k]
    logger.info(
        "retrieved_chunks",
        count=len(merged),
        machine_id=request.machine_id,
        scoped=len(scoped),
        unscoped=len(unscoped),
    )
    return merged
