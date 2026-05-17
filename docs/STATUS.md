# Implementation Status

Last updated: 2026-05-16

## Phases

| # | Phase | Status | Notes |
|---|-------|--------|-------|
| 1 | Skeleton: FastAPI + health + CI | ✅ Done | pyproject.toml, Makefile, Dockerfile, docker-compose, GH Actions |
| 2 | Pydantic models + Settings | ✅ Done | app/core/config.py, app/models/* |
| 3 | Synthetic data generator | ✅ Done | 12 machines, 120 tickets, 11,973 sensor readings, 20 manual sections, 60 operator notes |
| 4 | Ingestion pipeline + pgvector | ✅ Done | 233 chunks (20 manuals, 120 tickets, 33 anomaly summaries, 60 notes) embedded via Ollama nomic-embed-text into pgvector |
| 5 | Baseline `/ask` with RAG | ✅ Done | Retrieval + Ollama llama3.2 generation + heuristic grounding check; confidence 0.8, latency ~715ms |
| 6 | Agent workflow (intent → tools → answer) | ✅ Done | Keyword intent classifier (6 intents), 5 tools, custom orchestrator; wired into /ask |
| 7 | Eval framework + golden dataset | ✅ Done | 20 golden questions, evidence hit rate 1.0, CI gate passing; heuristic groundedness 0.23 (LLM judge deferred to later) |
| 8 | Prometheus metrics + Grafana dashboard | ✅ Done | /metrics live, all metric families present; Grafana dashboard JSON provisioned; Prometheus alerts wired |
| 9 | Feedback endpoint | ✅ Done | POST /feedback, GET /feedback, POST /feedback/{id}/promote; promote_feedback.py script; DB-persisted |
| 10 | README polish + demo | 🔲 Pending | |

## Legend
- ✅ Done — merged, tests pass, acceptance criteria met
- 🚧 In progress — actively being built
- 🔲 Pending — not started
- ❌ Blocked — waiting on dependency or decision

## Current focus

Phase 6 complete. Next: Phase 10 — README polish, architecture diagram, demo screenshots.

## Decisions log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-05-16 | Plain PostgreSQL + pgvector over TimescaleDB | Synthetic scale doesn't justify TimescaleDB ops overhead; can migrate later |
| 2026-05-16 | uv for dependency management | Faster than pip/poetry, lockfile native, dependency groups for dev/eval/data |
| 2026-05-16 | Custom agent orchestration (no LangGraph dependency) | Reduces framework coupling; easier to trace and test |
| 2026-05-16 | MLflow dropped from initial stack | No defined role at this scale; Prometheus + eval reports cover the use case |
| 2026-05-16 | Switched from OpenAI to Ollama | Local inference with llama3.2 + nomic-embed-text (768-dim); no API key needed |

## Related documents

- [plan.md](plan.md) — original design and architecture plan
- [architecture.md](architecture.md) — detailed architecture notes (to be written in Phase 1)
- [evaluation.md](evaluation.md) — evaluation framework design (to be written in Phase 7)
- [observability.md](observability.md) — observability setup (to be written in Phase 8)
