from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.agents.graph import run_agent
from app.core.logging import get_logger
from app.core.telemetry import rag_latency_seconds, rag_requests_total
from app.models.api import (
    AskRequest,
    AskResponse,
    IncidentDiagnoseRequest,
    IncidentSummarizeRequest,
    RetrievalMetadata,
)

logger = get_logger(__name__)
router = APIRouter()


@router.post("", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    """Answer an operational question using intent-driven agent + RAG."""
    t0 = time.perf_counter()
    answer_id = str(uuid.uuid4())

    logger.info(
        "ask_start", answer_id=answer_id, question=request.question, machine_id=request.machine_id
    )

    try:
        t_retrieval = time.perf_counter()
        result = await run_agent(request)
        retrieval_latency_ms = round((time.perf_counter() - t_retrieval) * 1000, 1)

        total_latency = time.perf_counter() - t0
        rag_latency_seconds.labels(endpoint="ask").observe(total_latency)
        rag_requests_total.labels(endpoint="ask", status="ok").inc()

        logger.info(
            "ask_complete",
            answer_id=answer_id,
            intent=result.intent,
            tools=result.tool_calls,
            grounded=result.grounded,
            confidence=result.confidence,
            latency_ms=round(total_latency * 1000, 1),
        )

        return AskResponse(
            answer_id=answer_id,
            question=request.question,
            answer=result.answer,
            sources=result.sources,
            confidence=result.confidence,
            grounded=result.grounded,
            retrieval_metadata=RetrievalMetadata(
                top_k=request.top_k,
                retrieval_latency_ms=retrieval_latency_ms,
                filters_applied=request.filters,
            ),
            intent=result.intent,
            tool_calls=result.tool_calls,
        )

    except Exception as exc:
        rag_requests_total.labels(endpoint="ask", status="error").inc()
        logger.error("ask_error", answer_id=answer_id, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc


@router.post("/incident/summarize", response_model=dict[str, Any])
async def summarize_incident(request: IncidentSummarizeRequest) -> dict[str, Any]:
    """Summarize a specific incident ticket via the agent."""
    ask_request = AskRequest(
        question=f"Summarize incident {request.ticket_id}. What happened, what was the root cause, and how was it resolved?",
        top_k=5,
    )
    response = await ask(ask_request)
    return {
        "ticket_id": request.ticket_id,
        "summary": response.answer,
        "sources": [s.model_dump() for s in response.sources],
        "intent": response.intent,
    }


@router.post("/incident/diagnose", response_model=dict[str, Any])
async def diagnose_incident(request: IncidentDiagnoseRequest) -> dict[str, Any]:
    """Run agent-based diagnosis for a reported symptom."""
    question = f"What are the likely causes and recommended actions for: {request.symptom}?"
    if request.machine_id:
        question += f" Machine: {request.machine_id}."

    ask_request = AskRequest(
        question=question,
        machine_id=request.machine_id,
        top_k=5,
    )
    response = await ask(ask_request)
    return {
        "symptom": request.symptom,
        "machine_id": request.machine_id,
        "diagnosis": response.answer,
        "sources": [s.model_dump() for s in response.sources],
        "grounded": response.grounded,
        "intent": response.intent,
        "tool_calls": response.tool_calls,
    }
