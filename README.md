# Operational AI Copilot

Production-grade RAG + agentic AI system for industrial operations — with evaluation, observability, and human-in-the-loop feedback.

[![CI](https://github.com/sylvainbonnot/operational-ai-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/sylvainbonnot/operational-ai-copilot/actions/workflows/ci.yml)

---

## Why this matters

Industrial AI systems fail when they are not grounded, observable, or operationally integrated.
A chatbot that hallucinates a root cause, or an LLM that ignores the maintenance manual, is worse than no AI at all.

This project demonstrates how to build a **reliable AI copilot** over machine data, maintenance history, and operational knowledge — with every design decision oriented toward correctness, traceability, and measurability.

---

## Features

| Capability | Implementation |
|---|---|
| RAG over manuals and incident tickets | pgvector + nomic-embed-text embeddings |
| Intent-driven agent workflows | Custom orchestrator — 6 intents, 5 tools |
| Synthetic industrial dataset | 12 machines, 120 tickets, ~12k sensor readings |
| Grounded answers with source citations | Heuristic + LLM-ready grounding check |
| Evaluation framework | 20 golden questions, evidence hit rate, CI gate |
| Prometheus / Grafana observability | 9 metric families, auto-provisioned dashboard |
| Human-in-the-loop feedback | `/feedback` API → golden dataset promotion |
| Dockerised deployment | One-command `make up` |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Synthetic Data Layer                      │
│  machines · tickets · sensor readings · manuals · notes     │
└──────────────────────────┬──────────────────────────────────┘
                           │  make seed-data + make ingest
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Storage Layer                           │
│  PostgreSQL + pgvector (chunks table, feedback table)       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Intent-Driven Agent Orchestrator               │
│                                                             │
│  Question → classify_intent()                               │
│      ↓                                                      │
│  diagnosis           → retrieve_incidents                   │
│                        retrieve_manuals                     │
│                        retrieve_anomalies                   │
│  summary             → retrieve_incidents                   │
│                        get_machine_history                  │
│  maintenance_rec.    → retrieve_manuals                     │
│                        retrieve_incidents                   │
│  risk_assessment     → retrieve_anomalies                   │
│                        get_machine_profile                  │
│      ↓                                                      │
│  generate_answer() via Ollama llama3.2                      │
│      ↓                                                      │
│  grounding_check() → confidence score                       │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Service                        │
│  POST /ask   POST /ask/incident/diagnose                    │
│  POST /ask/incident/summarize                               │
│  POST /feedback   GET /feedback                             │
│  POST /eval/run   GET /eval/reports                         │
│  GET  /metrics    GET /health                               │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│            Evaluation + Observability                       │
│  Prometheus metrics · Grafana dashboard · CI eval gate      │
│  20 golden questions · evidence hit rate · pass/fail report │
└─────────────────────────────────────────────────────────────┘
```

---

## Tech stack

**Backend:** Python 3.11 · FastAPI · Pydantic v2 · SQLAlchemy (async) · asyncpg

**AI:** Ollama (llama3.2 + nomic-embed-text) · custom agent orchestration

**Storage:** PostgreSQL + pgvector

**Evaluation:** Custom eval runner · JSONL golden dataset · CI-gated thresholds

**Observability:** Prometheus · Grafana · structlog

**Tooling:** uv · Makefile · Docker Compose · GitHub Actions

---

## Evaluation results

Run against 20 golden questions covering diagnosis, procedure lookup, anomaly analysis, and adversarial refusal:

| Metric | Score |
|---|---:|
| Evidence Hit Rate@8 | 1.00 |
| Pass Rate | 100% (20/20) |
| Mean Groundedness | 0.23 † |
| Mean Latency | ~42s ‡ |

† Heuristic groundedness (source ID citation count). LLM-based judge planned for next iteration.  
‡ Ollama running locally on CPU. GPU or cloud inference reduces this to ~2–3s.

---

## Quickstart

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) + Docker Compose
- [uv](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- [Ollama](https://ollama.com) with models pulled:
  ```bash
  ollama pull nomic-embed-text
  ollama pull llama3.2
  ```

### One-command setup

```bash
git clone https://github.com/sylvainbonnot/operational-ai-copilot
cd operational-ai-copilot

cp .env.example .env          # defaults point to local Ollama + Docker postgres

make install-all              # install all dependency groups
make up                       # start postgres + grafana + prometheus
make seed-data                # generate synthetic dataset (seed=42, deterministic)
make ingest                   # embed and store 233 chunks into pgvector
```

### Ask a question

```bash
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why did compressor_17 fail twice this month?",
    "machine_id": "compressor_17"
  }' | python3 -m json.tool
```

### Run evaluation

```bash
make eval
# → eval/reports/eval_YYYYMMDD_HHMMSS.md
```

### Run tests

```bash
make test
```

### Open dashboards

| Service | URL | Credentials |
|---|---|---|
| API docs | http://localhost:8000/docs | — |
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3000 | admin / admin |

---

## Project structure

```
operational-ai-copilot/
├── app/
│   ├── api/              # FastAPI route handlers
│   ├── agents/           # Intent classifier + tool definitions + orchestrator
│   ├── core/             # Config (pydantic-settings), logging, telemetry, middleware
│   ├── evaluation/       # Eval runner, metrics, dataset loader
│   ├── ingestion/        # Chunking strategies + per-type ingestors
│   ├── models/           # Pydantic domain models (machine, ticket, sensor, eval, api)
│   ├── rag/              # Retriever, prompts, answer generator, grounding check
│   └── storage/          # Database init, vector store, feedback store
├── data/                 # Synthetic data generator + generated files
├── docs/
│   ├── plan.md           # Original design and architecture plan
│   └── STATUS.md         # Live implementation tracker
├── eval/
│   ├── golden_questions.jsonl
│   └── reports/          # Eval run outputs (JSON + Markdown)
├── ops/
│   ├── prometheus/       # prometheus.yml + alerts.yml
│   ├── grafana/          # Auto-provisioning config
│   └── dashboards/       # copilot.json Grafana dashboard
├── scripts/              # Demo query, debug retrieval, promote feedback
├── tests/
├── Makefile
├── pyproject.toml        # uv project — dep groups: dev, eval, data
└── docker-compose.yml
```

---

## Makefile reference

```
make install-all   Install all dependency groups (dev, eval, data)
make up            Start all Docker services
make seed-data     Generate deterministic synthetic dataset (seed=42)
make ingest        Run ingestion pipeline → 233 chunks in pgvector
make eval          Run evaluation suite → report in eval/reports/
make test          Run test suite
make lint          Ruff check + format check
make typecheck     mypy
make demo          Run demo query script
make ci            lint + typecheck + test (CI entry point)
```

---

## API reference

### `POST /ask`

```json
{
  "question": "Why did compressor_17 fail twice this month?",
  "machine_id": "compressor_17",
  "top_k": 8
}
```

Response includes `answer`, `sources`, `confidence`, `grounded`, `intent`, `tool_calls`.

### `POST /ask/incident/diagnose`

```json
{
  "symptom": "abnormal vibration at startup",
  "machine_id": "compressor_17"
}
```

### `POST /feedback`

```json
{
  "question_id": "q_001",
  "answer_id": "a_abc123",
  "rating": "incorrect",
  "comment": "Root cause was coolant failure, not bearing wear.",
  "correct_source_id": "MANUAL-COOLING-01"
}
```

---

## Design decisions

See [docs/STATUS.md](docs/STATUS.md) for the full decisions log.

Key choices:

- **Ollama over OpenAI** — fully local, no API cost, reproducible for portfolio use
- **Custom agent orchestration over LangGraph** — reduces framework coupling, easier to trace and test
- **Plain PostgreSQL + pgvector over TimescaleDB** — right tool for synthetic scale; migrate if needed
- **Evidence hit rate over precision@k** — more meaningful when k >> expected evidence set size
- **Heuristic grounding over LLM judge** — fast and deterministic; LLM judge is the next iteration

---

## Recruiter summary

> Built an operational AI copilot for industrial incident analysis: RAG over maintenance tickets and manuals, intent-driven agentic workflows with 6 intent classes and 5 tools, time-series anomaly context, human-in-the-loop feedback loop, and Prometheus/Grafana observability. CI-gated evaluation suite with 20 golden questions measuring evidence hit rate, groundedness, and latency.
