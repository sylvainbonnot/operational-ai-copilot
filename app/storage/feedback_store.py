from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.core.logging import get_logger
from app.models.evaluation import FeedbackItem
from app.storage.database import get_session_factory

logger = get_logger(__name__)


async def save_feedback(item: FeedbackItem, question: str, answer: str) -> str:
    feedback_id = str(uuid.uuid4())
    session_factory = get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("""
                    INSERT INTO feedback
                        (id, question_id, answer_id, question, answer, rating,
                         comment, correct_source_id, reviewer_id, submitted_at)
                    VALUES
                        (:id, :question_id, :answer_id, :question, :answer, :rating,
                         :comment, :correct_source_id, :reviewer_id, :submitted_at)
                """),
                {
                    "id": feedback_id,
                    "question_id": item.question_id,
                    "answer_id": item.answer_id,
                    "question": question,
                    "answer": answer,
                    "rating": item.rating,
                    "comment": item.comment,
                    "correct_source_id": item.correct_source_id,
                    "reviewer_id": item.reviewer_id,
                    "submitted_at": item.submitted_at,
                },
            )
    logger.info("feedback_saved", feedback_id=feedback_id, rating=item.rating)
    return feedback_id


async def list_feedback(
    rating: str | None = None,
    promoted: bool | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: dict[str, Any] = {"limit": limit}
    if rating:
        clauses.append("rating = :rating")
        params["rating"] = rating
    if promoted is not None:
        clauses.append("promoted = :promoted")
        params["promoted"] = promoted

    sql = text(f"""
        SELECT id, question_id, answer_id, question, answer, rating,
               comment, correct_source_id, reviewer_id, promoted, submitted_at
        FROM feedback
        WHERE {" AND ".join(clauses)}
        ORDER BY submitted_at DESC
        LIMIT :limit
    """)
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(sql, params)
        rows = result.mappings().fetchall()
    return [dict(r) for r in rows]


async def mark_promoted(feedback_id: str) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        async with session.begin():
            await session.execute(
                text("UPDATE feedback SET promoted = true WHERE id = :id"),
                {"id": feedback_id},
            )
    logger.info("feedback_promoted", feedback_id=feedback_id)
