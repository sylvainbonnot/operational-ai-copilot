from __future__ import annotations

import json
from pathlib import Path

from app.core.logging import get_logger
from app.ingestion.chunking import chunk_ticket
from app.storage.vector_store import upsert_chunks

logger = get_logger(__name__)


async def ingest_tickets(data_dir: Path) -> int:
    path = data_dir / "tickets.jsonl"
    tickets = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    chunks = []
    for ticket in tickets:
        chunks.extend(chunk_ticket(ticket))
    await upsert_chunks(chunks)
    logger.info("ingested_tickets", count=len(chunks))
    return len(chunks)
