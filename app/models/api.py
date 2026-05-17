from typing import Any

from pydantic import BaseModel, Field


class SourceChunk(BaseModel):
    chunk_id: str
    source_type: str  # "ticket" | "manual" | "note" | "anomaly_summary"
    source_id: str
    machine_id: str | None = None
    content: str
    score: float = Field(ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalMetadata(BaseModel):
    top_k: int
    retrieval_latency_ms: float
    filters_applied: dict[str, Any] = Field(default_factory=dict)


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=1000)
    machine_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict[str, Any] = Field(default_factory=dict)


class AskResponse(BaseModel):
    answer_id: str
    question: str
    answer: str
    sources: list[SourceChunk]
    confidence: float = Field(ge=0.0, le=1.0)
    grounded: bool
    retrieval_metadata: RetrievalMetadata
    intent: str | None = None
    tool_calls: list[str] = Field(default_factory=list)


class IncidentSummarizeRequest(BaseModel):
    ticket_id: str
    include_history: bool = True


class IncidentDiagnoseRequest(BaseModel):
    symptom: str = Field(min_length=5)
    machine_id: str | None = None
    sensor_context: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str
    environment: str
