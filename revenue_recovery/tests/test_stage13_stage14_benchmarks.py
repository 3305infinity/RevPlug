"""Tests for Stage 13 (AI Judgment Engine) & Stage 14 (Recovery Economics & Batch Simulation)."""

import json
import os
import pytest

from app.datasets.synthetic import generate_evaluation_dataset
from app.domain.failures import FailureCategory
from app.domain.proposals import RecoveryAction
from app.services.evaluation_service import EvaluationService
from scripts.run_ai_benchmark import evaluate_provider


def test_stage13_dataset_generation_reproducibility():
    d1 = generate_evaluation_dataset(count=20, seed=42)
    d2 = generate_evaluation_dataset(count=20, seed=42)
    assert len(d1) == 20
    assert [x.id for x in d1] == [x.id for x in d2]


def test_stage13_deterministic_vs_hybrid_benchmark():
    dataset = generate_evaluation_dataset(count=15, seed=42)
    opted_out = set()

    res_det = evaluate_provider("deterministic", dataset, opted_out)
    res_hyb = evaluate_provider("hybrid", dataset, opted_out)

    assert res_det["total_cases"] == 15
    assert res_hyb["total_cases"] == 15
    assert res_det["safe_decision_rate"] == 1.0
    assert res_hyb["safe_decision_rate"] == 1.0
    assert res_det["policy_violations"] == 0
    assert res_hyb["policy_violations"] == 0


def test_stage14_financial_invariants():
    service = EvaluationService(ai_enabled=True)
    result = service.run_batch_evaluation(count=30, seed=101)

    gross_at_risk = result.revplug.total_amount_at_risk
    recovered = result.revplug.actual_recovered

    # Invariant: 0 <= recovered <= gross_at_risk
    assert 0 <= recovered <= gross_at_risk
    assert result.revplug.stopped_count >= 0
    assert result.revplug.safety_violations["total_safety_violations"] == 0


def test_stage14_benchmark_artifacts_exist():
    assert os.path.exists("artifacts/ai_benchmark.json")
    assert os.path.exists("artifacts/recovery_benchmark.json")
    assert os.path.exists("artifacts/recovery_benchmark.csv")

    with open("artifacts/ai_benchmark.json", "r", encoding="utf-8") as f:
        ai_data = json.load(f)
        assert "providers" in ai_data
        assert "deterministic" in ai_data["providers"]

    with open("artifacts/recovery_benchmark.json", "r", encoding="utf-8") as f:
        rec_data = json.load(f)
        assert "gross_at_risk_minor" in rec_data
        assert "revplug_recovered_minor" in rec_data
        assert rec_data["gross_at_risk_minor"] >= rec_data["revplug_recovered_minor"]
