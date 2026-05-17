from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.api import RetrievalMetadata, SourceChunk


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
    mock_chunks = [_make_chunk("INC-0001"), _make_chunk("INC-0002")]

    with (
        patch("app.api.routes_ask.retrieve", new_callable=AsyncMock, return_value=mock_chunks),
        patch(
            "app.api.routes_ask.generate_answer",
            new_callable=AsyncMock,
            return_value=type("R", (), {
                "answer": "Bearing wear was caused by lubrication failure (INC-0001, INC-0002).",
                "prompt_tokens": 200,
                "completion_tokens": 50,
                "latency_ms": 800.0,
            })(),
        ),
    ):
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
    assert data["retrieval_metadata"]["top_k"] == 5


@pytest.mark.asyncio
async def test_ask_no_chunks_returns_refusal() -> None:
    with patch("app.api.routes_ask.retrieve", new_callable=AsyncMock, return_value=[]):
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
