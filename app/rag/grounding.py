from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.api import SourceChunk

logger = get_logger(__name__)

# Phrases that indicate the model admitted it couldn't answer
_REFUSAL_PATTERNS = [
    r"i don.t have enough information",
    r"not enough information",
    r"cannot be found in",
    r"not mentioned in",
    r"no information (available|provided|found)",
    r"the (context|documents?) (do(es)? not|don.t) (contain|mention|include|provide)",
]
_REFUSAL_RE = re.compile("|".join(_REFUSAL_PATTERNS), re.IGNORECASE)


def compute_grounding_score(answer: str, chunks: list[SourceChunk]) -> float:
    """
    Heuristic grounding score: fraction of source IDs cited in the answer.
    Returns 0.0 if no sources, 1.0 if all sources are cited.
    A proper LLM-based grounding check will replace this in Phase 7.
    """
    if not chunks:
        return 0.0

    cited = sum(1 for chunk in chunks if chunk.source_id in answer)
    return round(cited / len(chunks), 3)


def is_grounded(answer: str, chunks: list[SourceChunk]) -> bool:
    """
    An answer is grounded if:
    - It cites at least one source ID, OR
    - It's a well-formed refusal (model correctly says it lacks information)
    """
    settings = get_settings()

    # Explicit refusal is considered grounded (model behaved correctly)
    if _REFUSAL_RE.search(answer):
        logger.info("grounding_refusal_detected")
        return True

    score = compute_grounding_score(answer, chunks)
    grounded = score >= settings.groundedness_threshold
    logger.info("grounding_check", score=score, grounded=grounded)
    return grounded
