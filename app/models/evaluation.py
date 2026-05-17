from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class GoldenQuestion(BaseModel):
    id: str
    question: str
    machine_id: str | None = None
    expected_evidence_ids: list[str] = Field(default_factory=list)
    expected_facts: list[str] = Field(default_factory=list)
    expected_refusal: bool = False


class EvalResult(BaseModel):
    question_id: str
    question: str
    answer: str
    sources_retrieved: list[str]
    retrieval_precision_at_k: float = Field(ge=0.0, le=1.0)
    retrieval_recall_at_k: float = Field(ge=0.0, le=1.0)
    groundedness: float = Field(ge=0.0, le=1.0)
    latency_ms: float = Field(ge=0.0)
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    passed: bool
    failure_reason: str | None = None


class EvalSummary(BaseModel):
    total: int
    passed: int
    failed: int
    pass_rate: float = Field(ge=0.0, le=1.0)
    mean_retrieval_precision: float
    mean_groundedness: float
    mean_latency_ms: float
    total_tokens: int
    estimated_cost_usd: float


class EvalReport(BaseModel):
    run_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    dataset_path: str
    results: list[EvalResult]
    summary: EvalSummary
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeedbackItem(BaseModel):
    question_id: str
    answer_id: str
    rating: str  # "correct" | "incorrect" | "partial"
    comment: str = ""
    correct_source_id: str | None = None
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    reviewer_id: str | None = None
