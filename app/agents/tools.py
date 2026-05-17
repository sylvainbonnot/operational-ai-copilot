from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.core.telemetry import agent_tool_calls_total
from app.models.api import SourceChunk
from app.storage.vector_store import similarity_search

logger = get_logger(__name__)

_DATA_DIR = Path("data/synthetic")


def _track(tool_name: str) -> None:
    agent_tool_calls_total.labels(tool_name=tool_name).inc()
    logger.info("tool_call", tool=tool_name)


async def tool_retrieve_incidents(machine_id: str | None, query: str, top_k: int = 5) -> list[SourceChunk]:
    """Retrieve relevant incident tickets."""
    _track("retrieve_incidents")
    filters: dict[str, Any] = {"source_type": "ticket"}
    if machine_id:
        filters["machine_id"] = machine_id
    chunks = await similarity_search(query, top_k=top_k, filters=filters)
    # Fallback to unscoped if too few results
    if len(chunks) < 2 and machine_id:
        chunks = await similarity_search(query, top_k=top_k, filters={"source_type": "ticket"})
    return chunks


async def tool_retrieve_manuals(query: str, top_k: int = 5) -> list[SourceChunk]:
    """Retrieve relevant manual sections."""
    _track("retrieve_manuals")
    return await similarity_search(query, top_k=top_k, filters={"source_type": "manual"})


async def tool_retrieve_anomalies(machine_id: str | None, query: str, top_k: int = 3) -> list[SourceChunk]:
    """Retrieve anomaly summaries for context."""
    _track("retrieve_anomalies")
    filters: dict[str, Any] = {"source_type": "anomaly_summary"}
    if machine_id:
        filters["machine_id"] = machine_id
    chunks = await similarity_search(query, top_k=top_k, filters=filters)
    if not chunks and machine_id:
        chunks = await similarity_search(query, top_k=top_k, filters={"source_type": "anomaly_summary"})
    return chunks


async def tool_get_machine_history(machine_id: str) -> list[SourceChunk]:
    """Retrieve all recent operator notes for a machine."""
    _track("get_machine_history")
    return await similarity_search(
        f"recent events and observations on {machine_id}",
        top_k=3,
        filters={"machine_id": machine_id, "source_type": "operator_note"},
    )


def tool_get_machine_profile(machine_id: str) -> dict[str, Any] | None:
    """Look up static machine metadata from the synthetic dataset."""
    _track("get_machine_profile")
    machines_path = _DATA_DIR / "machines.json"
    if not machines_path.exists():
        return None
    machines = json.loads(machines_path.read_text())
    return next((m for m in machines if m["machine_id"] == machine_id), None)
