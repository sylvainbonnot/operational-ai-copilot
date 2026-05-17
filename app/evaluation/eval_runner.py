"""
Evaluation runner for the Operational AI Copilot.

Usage:
    uv run python -m app.evaluation.eval_runner
    uv run python -m app.evaluation.eval_runner --dataset eval/golden_questions.jsonl --output eval/reports/
"""
from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from datetime import datetime
from pathlib import Path

from app.core.logging import configure_logging, get_logger
from app.core.telemetry import groundedness_score as groundedness_gauge
from app.core.telemetry import hallucination_rate as hallucination_gauge
from app.core.telemetry import retrieval_precision_at_k as precision_gauge
from app.evaluation.datasets import load_golden_questions
from app.evaluation.metrics import (
    compute_pass,
    evidence_hit_rate,
    fact_coverage,
    mrr,
    precision_at_k,
    recall_at_k,
    refusal_correct,
)
from app.models.api import AskRequest
from app.models.evaluation import EvalReport, EvalResult, EvalSummary
from app.rag.answer_generator import generate_answer
from app.rag.grounding import compute_grounding_score
from app.rag.retriever import retrieve

logger = get_logger(__name__)

# CI thresholds — fail the run if mean scores drop below these
THRESHOLD_HIT_RATE = 0.50
THRESHOLD_FACT_COVERAGE = 0.25
THRESHOLD_PASS_RATE = 0.60


async def run_eval(dataset_path: Path, output_dir: Path) -> EvalReport:
    configure_logging()
    questions = load_golden_questions(dataset_path)
    logger.info("eval_start", n_questions=len(questions), dataset=str(dataset_path))

    results: list[EvalResult] = []

    for q in questions:
        t0 = time.perf_counter()
        logger.info("eval_question", id=q.id, question=q.question[:60])

        request = AskRequest(
            question=q.question,
            machine_id=q.machine_id,
            top_k=8,
        )

        try:
            chunks = await retrieve(request)
            generation = await generate_answer(q.question, chunks)
            answer = generation.answer
        except Exception as exc:
            logger.error("eval_question_error", id=q.id, error=str(exc))
            answer = ""
            chunks = []
            generation = type("G", (), {"prompt_tokens": 0, "completion_tokens": 0, "latency_ms": 0.0})()

        latency_ms = round((time.perf_counter() - t0) * 1000, 1)
        retrieved_ids = [c.source_id for c in chunks]

        prec = precision_at_k(retrieved_ids, q.expected_evidence_ids)
        rec = recall_at_k(retrieved_ids, q.expected_evidence_ids)
        hit_rate = evidence_hit_rate(retrieved_ids, q.expected_evidence_ids)
        fact_cov = fact_coverage(answer, q.expected_facts)
        refusal_ok = refusal_correct(answer, q.expected_refusal)
        passed, failure_reason = compute_pass(
            hit_rate=hit_rate,
            fact_cov=fact_cov,
            refusal_ok=refusal_ok,
            expected_refusal=q.expected_refusal,
            hit_rate_threshold=THRESHOLD_HIT_RATE,
            fact_threshold=THRESHOLD_FACT_COVERAGE,
        )

        results.append(
            EvalResult(
                question_id=q.id,
                question=q.question,
                answer=answer,
                sources_retrieved=retrieved_ids,
                retrieval_precision_at_k=hit_rate,   # store hit_rate in this field for report
                retrieval_recall_at_k=rec,
                groundedness=compute_grounding_score(answer, chunks),
                latency_ms=latency_ms,
                prompt_tokens=generation.prompt_tokens,
                completion_tokens=generation.completion_tokens,
                passed=passed,
                failure_reason=failure_reason,
            )
        )

        status = "PASS" if passed else f"FAIL ({failure_reason})"
        logger.info("eval_result", id=q.id, status=status, hit_rate=hit_rate, recall=rec, fact_cov=fact_cov)

    # Aggregate summary
    n = len(results)
    n_passed = sum(1 for r in results if r.passed)
    summary = EvalSummary(
        total=n,
        passed=n_passed,
        failed=n - n_passed,
        pass_rate=round(n_passed / n, 4) if n else 0.0,
        mean_retrieval_precision=round(sum(r.retrieval_precision_at_k for r in results) / n, 4),
        mean_groundedness=round(sum(r.groundedness for r in results) / n, 4),
        mean_latency_ms=round(sum(r.latency_ms for r in results) / n, 1),
        total_tokens=sum(r.prompt_tokens + r.completion_tokens for r in results),
        estimated_cost_usd=0.0,  # Ollama is local — no cost
    )

    report = EvalReport(
        run_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow(),
        dataset_path=str(dataset_path),
        results=results,
        summary=summary,
    )

    # Push summary metrics into Prometheus gauges
    groundedness_gauge.set(summary.mean_groundedness)
    precision_gauge.set(summary.mean_retrieval_precision)
    n_ungrounded = sum(1 for r in results if r.groundedness < 0.3)
    hallucination_gauge.set(round(n_ungrounded / n, 4) if n else 0.0)
    logger.info("eval_metrics_pushed", groundedness=summary.mean_groundedness,
                precision=summary.mean_retrieval_precision)

    # Write report
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(report.model_dump_json(indent=2))

    # Also write a human-readable markdown summary
    md_path = output_dir / f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.md"
    md_path.write_text(_render_markdown(report))

    logger.info("eval_complete", pass_rate=summary.pass_rate, report=str(report_path))
    _print_summary(summary, results)

    return report


def _render_markdown(report: EvalReport) -> str:
    s = report.summary
    lines = [
        f"# Eval Report — {report.timestamp.strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Pass rate | {s.pass_rate:.0%} ({s.passed}/{s.total}) |",
        f"| Mean Evidence Hit Rate | {s.mean_retrieval_precision:.2f} |",
        f"| Mean Groundedness | {s.mean_groundedness:.2f} |",
        f"| Mean Latency | {s.mean_latency_ms:.0f}ms |",
        f"| Total tokens | {s.total_tokens:,} |",
        "",
        "## Results",
        "",
        "| ID | Question | Hit Rate | Recall | Groundedness | Pass |",
        "|----|----------|----------|--------|--------------|------|",
    ]
    for r in report.results:
        q_short = r.question[:50] + "..." if len(r.question) > 50 else r.question
        status = "✅" if r.passed else f"❌ {r.failure_reason or ''}"
        lines.append(
            f"| {r.question_id} | {q_short} | {r.retrieval_precision_at_k:.2f} | "
            f"{r.retrieval_recall_at_k:.2f} | {r.groundedness:.2f} | {status} |"
        )

    if any(not r.passed for r in report.results):
        lines += ["", "## Failures", ""]
        for r in report.results:
            if not r.passed:
                lines += [
                    f"### {r.question_id}: {r.question}",
                    f"- Reason: {r.failure_reason}",
                    f"- Retrieved: {', '.join(r.sources_retrieved) or 'none'}",
                    f"- Answer: {r.answer[:200]}...",
                    "",
                ]

    return "\n".join(lines)


def _print_summary(summary: EvalSummary, results: list[EvalResult]) -> None:
    print(f"\n{'='*55}")
    print(f"  Eval complete: {summary.passed}/{summary.total} passed ({summary.pass_rate:.0%})")
    print(f"{'='*55}")
    print(f"  Mean Evidence Hit Rate: {summary.mean_retrieval_precision:.3f}")
    print(f"  Mean Groundedness: {summary.mean_groundedness:.3f}")
    print(f"  Mean Latency     : {summary.mean_latency_ms:.0f}ms")
    print(f"  Total tokens     : {summary.total_tokens:,}")

    failures = [r for r in results if not r.passed]
    if failures:
        print(f"\n  Failures ({len(failures)}):")
        for r in failures:
            print(f"    [{r.question_id}] {r.failure_reason}")

    # CI gate check
    ci_failures = []
    if summary.pass_rate < THRESHOLD_PASS_RATE:
        ci_failures.append(f"pass_rate {summary.pass_rate:.0%} < {THRESHOLD_PASS_RATE:.0%}")
    if summary.mean_retrieval_precision < THRESHOLD_HIT_RATE:
        ci_failures.append(f"mean_hit_rate {summary.mean_retrieval_precision:.2f} < {THRESHOLD_HIT_RATE}")

    if ci_failures:
        print(f"\n  CI GATE FAILED:")
        for f in ci_failures:
            print(f"    ✗ {f}")
    else:
        print(f"\n  CI gate: ✓ all thresholds passed")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run evaluation suite")
    parser.add_argument("--dataset", type=Path, default=Path("eval/golden_questions.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("eval/reports/"))
    args = parser.parse_args()

    report = asyncio.run(run_eval(args.dataset, args.output))

    # Exit non-zero if CI gate failed
    if report.summary.pass_rate < THRESHOLD_PASS_RATE:
        raise SystemExit(1)
    if report.summary.mean_retrieval_precision < THRESHOLD_HIT_RATE:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
