.PHONY: install install-all test lint typecheck eval up down ingest seed-data demo ci clean

# ── Dependencies ──────────────────────────────────────────────────────────────

install:
	uv sync

install-all:
	uv sync --all-groups

# ── Quality ───────────────────────────────────────────────────────────────────

lint:
	uv run ruff check app/ tests/
	uv run ruff format --check app/ tests/

lint-fix:
	uv run ruff check --fix app/ tests/
	uv run ruff format app/ tests/

typecheck:
	uv run mypy app/

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=app --cov-report=html

# ── Infrastructure ────────────────────────────────────────────────────────────

up:
	docker compose up -d
	@echo "Waiting for postgres..."
	@sleep 3
	@echo "Services up. API: http://localhost:8000  Grafana: http://localhost:3000"

down:
	docker compose down

logs:
	docker compose logs -f app

# ── Data ──────────────────────────────────────────────────────────────────────

seed-data:
	uv run python -m data.generate --seed 42 --output data/synthetic/

ingest:
	uv run python -m app.ingestion.run_all

# ── Evaluation ────────────────────────────────────────────────────────────────

eval:
	uv run python -m app.evaluation.eval_runner \
		--dataset eval/golden_questions.jsonl \
		--output eval/reports/

eval-view:
	@ls -lt eval/reports/ | head -5

# ── Demo ──────────────────────────────────────────────────────────────────────

demo:
	uv run python scripts/demo_query.py

# ── CI (runs everything in order) ─────────────────────────────────────────────

ci: lint typecheck test

# ── Housekeeping ──────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	rm -f .coverage

help:
	@echo "Available targets:"
	@echo "  install      Install runtime dependencies"
	@echo "  install-all  Install all dependency groups (dev, eval, data)"
	@echo "  lint         Check code style"
	@echo "  lint-fix     Auto-fix code style issues"
	@echo "  typecheck    Run mypy"
	@echo "  test         Run test suite"
	@echo "  test-cov     Run tests with HTML coverage report"
	@echo "  up           Start all services via Docker Compose"
	@echo "  down         Stop all services"
	@echo "  logs         Follow app container logs"
	@echo "  seed-data    Generate synthetic dataset (deterministic, seed=42)"
	@echo "  ingest       Run ingestion pipeline"
	@echo "  eval         Run evaluation suite, write report to eval/reports/"
	@echo "  demo         Run demo query script"
	@echo "  ci           lint + typecheck + test (CI entry point)"
	@echo "  clean        Remove build/cache artifacts"
