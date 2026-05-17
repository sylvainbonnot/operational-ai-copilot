from __future__ import annotations

import re


def precision_at_k(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """Fraction of retrieved IDs that are in the expected set."""
    if not retrieved_ids:
        return 0.0
    hits = sum(1 for rid in retrieved_ids if rid in expected_ids)
    return round(hits / len(retrieved_ids), 4)


def recall_at_k(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """Fraction of expected IDs that appear in retrieved results."""
    if not expected_ids:
        return 1.0  # Nothing expected — trivially satisfied
    hits = sum(1 for eid in expected_ids if eid in retrieved_ids)
    return round(hits / len(expected_ids), 4)


def evidence_hit_rate(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """
    Fraction of expected evidence IDs that appear anywhere in the retrieved set.
    More meaningful than precision@k when k >> len(expected_ids).
    Returns 1.0 when expected_ids is empty (no specific evidence required).
    """
    if not expected_ids:
        return 1.0
    hits = sum(1 for eid in expected_ids if eid in retrieved_ids)
    return round(hits / len(expected_ids), 4)


def mrr(retrieved_ids: list[str], expected_ids: list[str]) -> float:
    """Mean Reciprocal Rank — rank of first relevant result."""
    for i, rid in enumerate(retrieved_ids, 1):
        if rid in expected_ids:
            return round(1.0 / i, 4)
    return 0.0


def fact_coverage(answer: str, expected_facts: list[str]) -> float:
    """
    Fraction of expected facts (case-insensitive substrings) found in the answer.
    Rough but fast — no LLM needed.
    """
    if not expected_facts:
        return 1.0
    hits = sum(1 for fact in expected_facts if fact.lower() in answer.lower())
    return round(hits / len(expected_facts), 4)


def refusal_correct(answer: str, expected_refusal: bool) -> bool:
    """Check whether refusal behaviour matches expectation."""
    _REFUSAL_RE = re.compile(
        r"i don.t have enough information|not enough information|"
        r"cannot be found in|not mentioned in|"
        r"no information (available|provided|found)|"
        r"the (context|documents?) (do(es)? not|don.t) (contain|mention|include|provide)",
        re.IGNORECASE,
    )
    answer_is_refusal = bool(_REFUSAL_RE.search(answer))
    return answer_is_refusal == expected_refusal


def compute_pass(
    hit_rate: float,
    fact_cov: float,
    refusal_ok: bool,
    expected_refusal: bool,
    hit_rate_threshold: float = 0.5,
    fact_threshold: float = 0.25,
) -> tuple[bool, str | None]:
    """
    Return (passed, failure_reason).
    Refusal questions only check refusal_correct; factual questions check all thresholds.
    Gates on evidence_hit_rate (did we find the expected docs?) and fact_coverage.
    """
    if not refusal_ok:
        return False, f"refusal_mismatch (expected_refusal={expected_refusal})"
    if expected_refusal:
        return True, None  # Refusal question passed
    if hit_rate < hit_rate_threshold:
        return False, f"evidence_hit_rate {hit_rate:.2f} < {hit_rate_threshold}"
    if fact_cov < fact_threshold:
        return False, f"fact_coverage {fact_cov:.2f} < {fact_threshold}"
    return True, None
