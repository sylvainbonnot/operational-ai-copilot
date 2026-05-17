from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query, status

from app.core.logging import get_logger
from app.models.evaluation import FeedbackItem
from app.storage.feedback_store import list_feedback, mark_promoted, save_feedback

logger = get_logger(__name__)
router = APIRouter()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_feedback(item: FeedbackItem) -> dict[str, str]:
    """
    Accept human feedback on a copilot answer.

    The feedback is persisted and can be promoted to the golden eval dataset
    via POST /feedback/{id}/promote or the scripts/promote_feedback.py script.
    """
    # question/answer text isn't in FeedbackItem — store empty strings for now;
    # a richer integration would look them up from an answer cache by answer_id.
    feedback_id = await save_feedback(item, question="", answer="")
    return {"feedback_id": feedback_id, "status": "accepted"}


@router.get("", response_model=list[dict[str, Any]])
async def get_feedback(
    rating: str | None = Query(default=None, description="Filter by rating: correct, incorrect, partial"),
    promoted: bool | None = Query(default=None, description="Filter by promotion status"),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[dict[str, Any]]:
    """List submitted feedback items."""
    items = await list_feedback(rating=rating, promoted=promoted, limit=limit)
    # Convert datetime objects for JSON serialisation
    return [
        {**item, "submitted_at": item["submitted_at"].isoformat() if item.get("submitted_at") else None}
        for item in items
    ]


@router.post("/{feedback_id}/promote", status_code=status.HTTP_200_OK)
async def promote_feedback(feedback_id: str) -> dict[str, str]:
    """
    Mark a feedback item as promoted to the golden eval dataset.
    Use scripts/promote_feedback.py to actually write it to eval/golden_questions.jsonl.
    """
    await mark_promoted(feedback_id)
    return {"feedback_id": feedback_id, "status": "promoted"}
