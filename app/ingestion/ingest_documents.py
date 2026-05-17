from __future__ import annotations

import json
from pathlib import Path

from app.core.logging import get_logger
from app.ingestion.chunking import chunk_manual_section, chunk_operator_note
from app.storage.vector_store import upsert_chunks

logger = get_logger(__name__)


async def ingest_manuals(data_dir: Path) -> int:
    path = data_dir / "manual_sections.json"
    sections = json.loads(path.read_text())
    chunks = []
    for section in sections:
        chunks.extend(chunk_manual_section(section))
    await upsert_chunks(chunks)
    logger.info("ingested_manuals", count=len(chunks))
    return len(chunks)


async def ingest_operator_notes(data_dir: Path) -> int:
    path = data_dir / "operator_notes.jsonl"
    notes = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    chunks = []
    for note in notes:
        chunks.extend(chunk_operator_note(note))
    await upsert_chunks(chunks)
    logger.info("ingested_operator_notes", count=len(chunks))
    return len(chunks)
