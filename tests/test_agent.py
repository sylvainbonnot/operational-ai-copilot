from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.agents.intent import classify_intent
from app.main import app
from app.models.api import SourceChunk

# ── Intent classifier ─────────────────────────────────────────────────────────

def test_intent_diagnosis() -> None:
    assert classify_intent("Why did compressor_17 fail last month?") == "diagnosis"


def test_intent_summary() -> None:
    assert classify_intent("Summarize recent anomalies on Line 3.") == "summary"


def test_intent_similar_incidents() -> None:
    assert classify_intent("Which past incidents resemble this vibration pattern?") == "similar_incidents"


def test_intent_maintenance_recommendation() -> None:
    assert classify_intent("What should an operator check first?") == "maintenance_recommendation"


def test_intent_risk_assessment() -> None:
    assert classify_intent("What is the risk of compressor_17 failing again?") == "risk_assessment"


def test_intent_unknown() -> None:
    assert classify_intent("Hello there") == "unknown"


# ── /ask route with agent ─────────────────────────────────────────────────────

def _make_chunk(source_id: str = "INC-0001") -> SourceChunk:
    return SourceChunk(
        chunk_id=f"chunk-ticket-{source_id}",
        source_type="ticket",
        source_id=source_id,
        machine_id="compressor_17",
        content=f"Incident {source_id} — bearing wear. Root cause: lubrication failure.",
        score=0.88,
    )


@pytest.mark.asyncio
async def test_ask_with_agent_returns_intent_and_tools() -> None:
    from app.agents.graph import AgentResult

    mock_result = AgentResult(
        answer="Bearing wear was caused by lubrication failure (INC-0001).",
        sources=[_make_chunk("INC-0001"), _make_chunk("INC-0002")],
        intent="diagnosis",
        tool_calls=["retrieve_incidents", "retrieve_manuals", "retrieve_anomalies"],
        grounded=True,
        confidence=0.75,
        prompt_tokens=200,
        completion_tokens=60,
        latency_ms=900.0,
    )

    with patch("app.api.routes_ask.run_agent", new_callable=AsyncMock, return_value=mock_result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/ask",
                json={"question": "Why did compressor_17 fail?", "machine_id": "compressor_17"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "diagnosis"
    assert "retrieve_incidents" in data["tool_calls"]
    assert data["grounded"] is True
    assert len(data["sources"]) == 2


@pytest.mark.asyncio
async def test_ask_maintenance_intent_uses_manuals() -> None:
    from app.agents.graph import AgentResult

    mock_result = AgentResult(
        answer="Check bearing clearance per MANUAL-COMP-01.",
        sources=[_make_chunk("MANUAL-COMP-01")],
        intent="maintenance_recommendation",
        tool_calls=["retrieve_manuals", "retrieve_incidents"],
        grounded=True,
        confidence=0.8,
    )

    with patch("app.api.routes_ask.run_agent", new_callable=AsyncMock, return_value=mock_result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/ask",
                json={"question": "What should an operator check first for vibration?"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "maintenance_recommendation"
    assert "retrieve_manuals" in data["tool_calls"]
