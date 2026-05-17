from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.api import SourceChunk


def _make_chunk(source_id: str = "INC-0001") -> SourceChunk:
    return SourceChunk(
        chunk_id=f"chunk-ticket-{source_id}",
        source_type="ticket",
        source_id=source_id,
        machine_id="compressor_17",
        content=f"Incident {source_id} — bearing wear on compressor_17. Root cause: lubrication failure.",
        score=0.91,
    )


@pytest.mark.asyncio
async def test_ask_returns_answer() -> None:
    from app.agents.graph import AgentResult

    mock_chunks = [_make_chunk("INC-0001"), _make_chunk("INC-0002")]
    mock_result = AgentResult(
        answer="Bearing wear was caused by lubrication failure (INC-0001, INC-0002).",
        sources=mock_chunks,
        intent="diagnosis",
        tool_calls=["retrieve_incidents", "retrieve_manuals"],
        grounded=True,
        confidence=0.75,
        prompt_tokens=200,
        completion_tokens=50,
        latency_ms=800.0,
    )

    with patch("app.api.routes_ask.run_agent", new_callable=AsyncMock, return_value=mock_result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/ask",
                json={"question": "Why did compressor_17 fail?", "machine_id": "compressor_17"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] != ""
    assert data["grounded"] is True
    assert len(data["sources"]) == 2
    assert "answer_id" in data


@pytest.mark.asyncio
async def test_ask_no_chunks_returns_refusal() -> None:
    from app.agents.graph import AgentResult

    mock_result = AgentResult(
        answer="I don't have enough information to answer this question.",
        sources=[],
        intent="unknown",
        tool_calls=[],
        grounded=True,
        confidence=0.0,
    )

    with patch("app.api.routes_ask.run_agent", new_callable=AsyncMock, return_value=mock_result):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/ask",
                json={"question": "What is the maintenance schedule for compressor_99?"},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] is True
    assert data["confidence"] == 0.0
    assert "don't have enough information" in data["answer"]


@pytest.mark.asyncio
async def test_ask_validation_rejects_short_question() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/ask", json={"question": "hi"})
    assert response.status_code == 422
