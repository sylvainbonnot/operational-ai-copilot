from __future__ import annotations

import json
from pathlib import Path

from app.core.logging import get_logger
from app.ingestion.chunking import chunk_anomaly_summary
from app.storage.vector_store import upsert_chunks

logger = get_logger(__name__)


async def ingest_anomaly_summaries(data_dir: Path) -> int:
    path = data_dir / "anomaly_summaries.jsonl"
    summaries = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    chunks = []
    for summary in summaries:
        chunks.extend(chunk_anomaly_summary(summary))
    await upsert_chunks(chunks)
    logger.info("ingested_anomaly_summaries", count=len(chunks))
    return len(chunks)
