from __future__ import annotations

from dataclasses import dataclass

from app.agents.intent import IntentType, classify_intent
from app.agents.tools import (
    tool_get_machine_history,
    tool_get_machine_profile,
    tool_retrieve_anomalies,
    tool_retrieve_incidents,
    tool_retrieve_manuals,
)
from app.core.logging import get_logger
from app.models.api import AskRequest, SourceChunk
from app.rag.answer_generator import GenerationResult, generate_answer
from app.rag.grounding import compute_grounding_score, is_grounded

logger = get_logger(__name__)


@dataclass
class AgentResult:
    answer: str
    sources: list[SourceChunk]
    intent: IntentType
    tool_calls: list[str]
    grounded: bool
    confidence: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


async def run_agent(request: AskRequest) -> AgentResult:
    """
    Intent-driven agent orchestration.

    1. Classify intent from question text.
    2. Select and run tools based on intent.
    3. Merge context, deduplicate by chunk_id.
    4. Generate grounded answer.
    """
    intent = classify_intent(request.question)
    machine_id = request.machine_id
    question = request.question
    top_k = request.top_k or 5
    tool_calls: list[str] = []
    context_chunks: list[SourceChunk] = []

    logger.info("agent_start", intent=intent, machine_id=machine_id)

    if intent == "diagnosis":
        # Need incidents + manuals + anomaly context
        incidents = await tool_retrieve_incidents(machine_id, question, top_k=5)
        tool_calls.append("retrieve_incidents")
        manuals = await tool_retrieve_manuals(question, top_k=3)
        tool_calls.append("retrieve_manuals")
        anomalies = await tool_retrieve_anomalies(machine_id, question, top_k=3)
        tool_calls.append("retrieve_anomalies")
        context_chunks = incidents + manuals + anomalies

    elif intent == "summary":
        # Need incidents + operator notes for the machine
        incidents = await tool_retrieve_incidents(machine_id, question, top_k=5)
        tool_calls.append("retrieve_incidents")
        if machine_id:
            history = await tool_get_machine_history(machine_id)
            tool_calls.append("get_machine_history")
            context_chunks = incidents + history
        else:
            context_chunks = incidents

    elif intent == "similar_incidents":
        incidents = await tool_retrieve_incidents(machine_id, question, top_k=top_k)
        tool_calls.append("retrieve_incidents")
        context_chunks = incidents

    elif intent == "maintenance_recommendation":
        # Need manuals first, then incidents for precedent
        manuals = await tool_retrieve_manuals(question, top_k=5)
        tool_calls.append("retrieve_manuals")
        incidents = await tool_retrieve_incidents(machine_id, question, top_k=3)
        tool_calls.append("retrieve_incidents")
        context_chunks = manuals + incidents

    elif intent == "risk_assessment":
        # Need machine profile + anomalies + incidents
        anomalies = await tool_retrieve_anomalies(machine_id, question, top_k=4)
        tool_calls.append("retrieve_anomalies")
        incidents = await tool_retrieve_incidents(machine_id, question, top_k=4)
        tool_calls.append("retrieve_incidents")
        if machine_id:
            profile = tool_get_machine_profile(machine_id)
            tool_calls.append("get_machine_profile")
            # Inject profile as a synthetic chunk if found
            if profile:
                from app.models.api import SourceChunk

                profile_chunk = SourceChunk(
                    chunk_id=f"profile-{machine_id}",
                    source_type="machine_profile",
                    source_id=machine_id,
                    machine_id=machine_id,
                    content=(
                        f"Machine profile: {machine_id}\n"
                        f"Type: {profile.get('machine_type')} | Component: {profile.get('component')}\n"
                        f"Risk level: {profile.get('risk_level')} | Site: {profile.get('site')}"
                    ),
                    score=1.0,
                )
                context_chunks = [profile_chunk] + anomalies + incidents
            else:
                context_chunks = anomalies + incidents
        else:
            context_chunks = anomalies + incidents

    else:
        # unknown — fall back to broad retrieval across all types
        from app.rag.retriever import retrieve

        context_chunks = await retrieve(request)
        tool_calls.append("retrieve_broad")

    # Deduplicate by chunk_id, preserve order (first occurrence wins)
    seen: set[str] = set()
    deduped: list[SourceChunk] = []
    for chunk in context_chunks:
        if chunk.chunk_id not in seen:
            seen.add(chunk.chunk_id)
            deduped.append(chunk)

    # Cap total context
    deduped = deduped[: top_k + 3]

    if not deduped:
        return AgentResult(
            answer="I don't have enough information in the retrieved documents to answer this question.",
            sources=[],
            intent=intent,
            tool_calls=tool_calls,
            grounded=True,
            confidence=0.0,
        )

    generation: GenerationResult = await generate_answer(question, deduped)
    grounded = is_grounded(generation.answer, deduped)
    confidence = compute_grounding_score(generation.answer, deduped)

    logger.info(
        "agent_complete", intent=intent, tools=tool_calls, chunks=len(deduped), grounded=grounded
    )

    return AgentResult(
        answer=generation.answer,
        sources=deduped,
        intent=intent,
        tool_calls=tool_calls,
        grounded=grounded,
        confidence=confidence,
        prompt_tokens=generation.prompt_tokens,
        completion_tokens=generation.completion_tokens,
        latency_ms=generation.latency_ms,
    )
