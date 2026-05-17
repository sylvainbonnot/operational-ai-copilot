from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/run", response_model=dict[str, Any])
async def run_eval(dataset: str = "eval/golden_questions.jsonl") -> dict[str, Any]:
    """Trigger an evaluation run against the golden dataset."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet")


@router.get("/reports", response_model=list[str])
async def list_reports() -> list[str]:
    """List available evaluation report files."""
    import os

    reports_dir = "eval/reports"
    if not os.path.isdir(reports_dir):
        return []
    return sorted(os.listdir(reports_dir), reverse=True)
