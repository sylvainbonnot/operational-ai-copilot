from __future__ import annotations

import re
from typing import Literal

IntentType = Literal[
    "diagnosis",
    "summary",
    "similar_incidents",
    "maintenance_recommendation",
    "risk_assessment",
    "unknown",
]

# Keyword-based classifier — fast, no LLM call needed, deterministic
_RULES: list[tuple[re.Pattern[str], IntentType]] = [
    (
        re.compile(r"\b(why|cause|root.cause|fail|fault|broke|broke down|failure)\b", re.I),
        "diagnosis",
    ),
    (
        re.compile(
            r"\b(summar|overview|what happened|recent|history|last month|this month)\b", re.I
        ),
        "summary",
    ),
    (
        re.compile(r"\b(similar|like|resemble|same as|past incident|previous)\b", re.I),
        "similar_incidents",
    ),
    (
        re.compile(
            r"\b(should|recommend|next step|what to do|check first|procedure|how to)\b", re.I
        ),
        "maintenance_recommendation",
    ),
    (
        re.compile(r"\b(risk|danger|safe|critical|urgent|probability|likely to fail)\b", re.I),
        "risk_assessment",
    ),
]


def classify_intent(question: str) -> IntentType:
    for pattern, intent in _RULES:
        if pattern.search(question):
            return intent
    return "unknown"
