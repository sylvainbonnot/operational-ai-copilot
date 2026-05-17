from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.telemetry import llm_latency_seconds
from app.models.api import SourceChunk
from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt

logger = get_logger(__name__)


@dataclass
class GenerationResult:
    answer: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


async def generate_answer(question: str, chunks: list[SourceChunk]) -> GenerationResult:
    """Call Ollama /api/chat and return the answer with usage stats."""
    settings = get_settings()
    url = f"{settings.ollama_base_url}/api/chat"

    user_prompt = build_user_prompt(question, chunks)

    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {
            "temperature": 0.1,  # Low temperature for factual, grounded answers
            "num_ctx": settings.max_context_tokens,
        },
    }

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()

    latency = time.perf_counter() - t0
    llm_latency_seconds.labels(model=settings.llm_model).observe(latency)

    data = response.json()
    answer = data["message"]["content"].strip()

    # Ollama usage stats (may not always be present)
    prompt_tokens = data.get("prompt_eval_count", 0)
    completion_tokens = data.get("eval_count", 0)

    logger.info(
        "llm_generation",
        model=settings.llm_model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=round(latency * 1000, 1),
    )

    return GenerationResult(
        answer=answer,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=round(latency * 1000, 1),
    )
