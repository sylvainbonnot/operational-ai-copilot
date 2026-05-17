from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_submit_feedback_accepted() -> None:
    with patch(
        "app.api.routes_feedback.save_feedback",
        new_callable=AsyncMock,
        return_value="test-feedback-id",
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/feedback",
                json={
                    "question_id": "q_001",
                    "answer_id": "a_abc123",
                    "rating": "incorrect",
                    "comment": "Root cause was coolant failure, not bearing wear.",
                    "correct_source_id": "MANUAL-COOLING-01",
                },
            )

    assert response.status_code == 202
    data = response.json()
    assert data["feedback_id"] == "test-feedback-id"
    assert data["status"] == "accepted"


@pytest.mark.asyncio
async def test_submit_feedback_invalid_missing_fields() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/feedback", json={"rating": "incorrect"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_feedback_empty() -> None:
    with patch(
        "app.api.routes_feedback.list_feedback",
        new_callable=AsyncMock,
        return_value=[],
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/feedback")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_promote_feedback() -> None:
    with patch(
        "app.api.routes_feedback.mark_promoted",
        new_callable=AsyncMock,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/feedback/some-id/promote")
    assert response.status_code == 200
    assert response.json()["status"] == "promoted"
