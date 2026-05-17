from __future__ import annotations

import pytest

from app.evaluation.metrics import (
    compute_pass,
    evidence_hit_rate,
    fact_coverage,
    mrr,
    precision_at_k,
    recall_at_k,
    refusal_correct,
)


def test_precision_perfect() -> None:
    assert precision_at_k(["A", "B"], ["A", "B", "C"]) == 1.0


def test_precision_partial() -> None:
    assert precision_at_k(["A", "X"], ["A", "B"]) == 0.5


def test_precision_empty_retrieved() -> None:
    assert precision_at_k([], ["A"]) == 0.0


def test_recall_perfect() -> None:
    assert recall_at_k(["A", "B", "C"], ["A", "B"]) == 1.0


def test_recall_partial() -> None:
    assert recall_at_k(["A", "X"], ["A", "B"]) == 0.5


def test_recall_no_expected() -> None:
    # No expected evidence — trivially passes
    assert recall_at_k(["A"], []) == 1.0


def test_mrr_first_hit() -> None:
    assert mrr(["A", "B", "C"], ["A"]) == 1.0


def test_mrr_second_hit() -> None:
    assert mrr(["X", "A", "B"], ["A"]) == pytest.approx(0.5)


def test_mrr_no_hit() -> None:
    assert mrr(["X", "Y"], ["A"]) == 0.0


def test_evidence_hit_rate_all_found() -> None:
    assert evidence_hit_rate(["MANUAL-COMP-01", "INC-0042", "NOTE-01"], ["MANUAL-COMP-01", "INC-0042"]) == 1.0


def test_evidence_hit_rate_partial() -> None:
    assert evidence_hit_rate(["MANUAL-COMP-01", "INC-0099"], ["MANUAL-COMP-01", "INC-0042"]) == 0.5


def test_evidence_hit_rate_no_expected() -> None:
    assert evidence_hit_rate(["anything"], []) == 1.0


def test_fact_coverage_all() -> None:
    assert fact_coverage("The bearing clearance is 0.04-0.08 mm", ["0.04-0.08 mm", "bearing clearance"]) == 1.0


def test_fact_coverage_partial() -> None:
    score = fact_coverage("The bearing clearance is correct", ["0.04-0.08 mm", "bearing clearance"])
    assert score == 0.5


def test_fact_coverage_no_facts() -> None:
    assert fact_coverage("anything", []) == 1.0


def test_refusal_correct_expected_and_present() -> None:
    answer = "I don't have enough information in the retrieved documents to answer this question."
    assert refusal_correct(answer, expected_refusal=True) is True


def test_refusal_correct_not_expected_not_present() -> None:
    assert refusal_correct("The bearing should be replaced.", expected_refusal=False) is True


def test_refusal_mismatch_expected_not_present() -> None:
    assert refusal_correct("The bearing should be replaced.", expected_refusal=True) is False


def test_refusal_mismatch_not_expected_but_present() -> None:
    answer = "I don't have enough information to answer."
    assert refusal_correct(answer, expected_refusal=False) is False


def test_compute_pass_all_good() -> None:
    passed, reason = compute_pass(
        hit_rate=0.8, fact_cov=0.8,
        refusal_ok=True, expected_refusal=False,
    )
    assert passed is True
    assert reason is None


def test_compute_pass_low_hit_rate() -> None:
    passed, reason = compute_pass(
        hit_rate=0.1, fact_cov=0.8,
        refusal_ok=True, expected_refusal=False,
    )
    assert passed is False
    assert "evidence_hit_rate" in reason  # type: ignore[operator]


def test_compute_pass_refusal_question() -> None:
    # Refusal questions skip hit_rate/fact checks
    passed, reason = compute_pass(
        hit_rate=0.0, fact_cov=0.0,
        refusal_ok=True, expected_refusal=True,
    )
    assert passed is True
    assert reason is None
