from __future__ import annotations

from app.models.api import SourceChunk

SYSTEM_PROMPT = """\
You are an Operational AI Copilot for industrial environments.
You help operators and maintenance engineers diagnose incidents, understand machine history, and decide on corrective actions.

Rules:
- Answer ONLY based on the provided context. Do not use general knowledge.
- If the context does not contain enough information to answer, say: "I don't have enough information in the retrieved documents to answer this question."
- Always cite the source IDs that support your answer (e.g. INC-0042, MANUAL-COMP-01).
- Be concise and practical. Operators need actionable answers.
- If the question involves safety, always mention relevant safety procedures.
"""


def build_user_prompt(question: str, chunks: list[SourceChunk]) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        context_parts.append(
            f"[{i}] Source: {chunk.source_id} (type: {chunk.source_type})\n{chunk.content}"
        )
    context = "\n\n---\n\n".join(context_parts)

    return f"""\
Context documents:

{context}

---

Question: {question}

Answer (cite source IDs inline):"""
