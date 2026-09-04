from datetime import datetime, timezone

import pytest

from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.scoring.expected_value import ExpectedValueScorer, ScoreResult
from app.scoring.priority import PriorityClassifier
from app.scoring.probability import RecoveryProbabilityModel


@pytest.fixture
def utcnow():
    return datetime(2026, 8, 26, 9, 0, 0, tzinfo=timezone.utc)


def test_basic_calculation():
    scorer = ExpectedValueScorer()
    result = scorer.score(
        amount_minor=50_000,  # ₹500
        failure_category="soft",
        proposed_action="retry_payment",
    )
    assert result.amount_at_risk == 50_000
    assert result.recovery_probability == pytest.approx(0.70)
    assert result.intervention_cost == 500
    assert result.expected_recovery_value == 34_500  # 50000 * 0.7 - 500
    assert result.priority == "HIGH"
    assert result.score_version == "v1"


def test_highest_amount_not_highest_priority():
    scorer = ExpectedValueScorer()
    case_a = scorer.score(
        amount_minor=100_000,  # ₹1,000
        failure_category="soft",
        proposed_action="retry_payment",
    )
    case_b = scorer.score(
        amount_minor=20_000,  # ₹200
        failure_category="fraud",
        proposed_action="escalate_human",
    )
    # Case A: 100000 * 0.7 - 500 = 69500 (CRITICAL)
    # Case B: 20000 * 0.2 - 1000 = 3000 (MEDIUM)
    assert case_a.expected_recovery_value == 69_500
    assert case_b.expected_recovery_value == 3_000
    assert case_a.expected_recovery_value > case_b.expected_recovery_value


def test_highest_probability_not_highest_priority():
    scorer = ExpectedValueScorer()
    case_a = scorer.score(
        amount_minor=30_000,  # ₹300
        failure_category="soft",
        proposed_action="retry_payment",
    )
    case_b = scorer.score(
        amount_minor=60_000,  # ₹600
        failure_category="hard",
        proposed_action="send_payment_link",
    )
    # Case A: 30000 * 0.7 - 500 = 20500 (HIGH)
    # Case B: 60000 * 0.55 - 200 = 32800 (HIGH)
    assert case_a.expected_recovery_value == 20_500
    assert case_b.expected_recovery_value == 32_800
    assert case_b.expected_recovery_value > case_a.expected_recovery_value
    assert case_a.priority == "HIGH"
    assert case_b.priority == "HIGH"


def test_intervention_cost_matters():
    scorer = ExpectedValueScorer()
    cheap = scorer.score(
        amount_minor=100_000,
        failure_category="soft",
        proposed_action="retry_payment",
    )
    expensive = scorer.score(
        amount_minor=100_000,
        failure_category="soft",
        proposed_action="escalate_human",
    )
    assert cheap.expected_recovery_value > expensive.expected_recovery_value
    assert cheap.intervention_cost == 500
    assert expensive.intervention_cost == 1000


def test_determinism():
    scorer = ExpectedValueScorer()
    results = [
        scorer.score(
            amount_minor=123_456,
            failure_category="soft",
            proposed_action="retry_payment",
        )
        for _ in range(1000)
    ]
    values = [r.expected_recovery_value for r in results]
    assert len(set(values)) == 1


def test_monetary_precision():
    scorer = ExpectedValueScorer()
    result = scorer.score(
        amount_minor=100_100,  # ₹1,001
        failure_category="soft",
        proposed_action="retry_payment",
    )
    expected = int(100_100 * 0.70) - 500
    assert result.expected_recovery_value == expected
    assert isinstance(result.expected_recovery_value, int)


def test_fraud_has_zero_probability():
    scorer = ExpectedValueScorer()
    result = scorer.score(
        amount_minor=50_000,
        failure_category="fraud",
        proposed_action="stop_recovery",
    )
    assert result.recovery_probability == pytest.approx(0.0)
    assert result.expected_recovery_value == 0
    assert result.intervention_cost == 0


def test_retry_degradation():
    prob_model = RecoveryProbabilityModel()
    attempt_1 = prob_model.estimate("soft", "retry_payment", attempt_number=1)
    attempt_2 = prob_model.estimate("soft", "retry_payment", attempt_number=2)
    attempt_3 = prob_model.estimate("soft", "retry_payment", attempt_number=3)
    assert attempt_1 == pytest.approx(0.70)
    assert attempt_2 == pytest.approx(0.55)
    assert attempt_3 == pytest.approx(0.40)


def test_priority_classifier():
    classifier = PriorityClassifier()
    assert classifier.classify(0) == "LOW"
    assert classifier.classify(4999) == "LOW"
    assert classifier.classify(5000) == "MEDIUM"
    assert classifier.classify(19999) == "MEDIUM"
    assert classifier.classify(20000) == "HIGH"
    assert classifier.classify(49999) == "HIGH"
    assert classifier.classify(50000) == "CRITICAL"
    assert classifier.classify(100_000) == "CRITICAL"


def test_score_result_is_dataclass():
    scorer = ExpectedValueScorer()
    result = scorer.score(
        amount_minor=100_000,
        failure_category="soft",
        proposed_action="retry_payment",
    )
    assert isinstance(result, ScoreResult)
    assert result.amount_at_risk == 100_000
    assert result.scoring_reason != ""


def test_unknown_category_fallback():
    scorer = ExpectedValueScorer()
    result = scorer.score(
        amount_minor=100_000,
        failure_category="nonexistent_category",
        proposed_action="retry_payment",
    )
    assert result.recovery_probability == pytest.approx(0.10)  # fallback to unknown default
    assert result.expected_recovery_value >= 0


def test_score_includes_all_required_fields():
    scorer = ExpectedValueScorer()
    result = scorer.score(
        amount_minor=50_000,
        failure_category="hard",
        proposed_action="send_payment_link",
    )
    assert result.amount_at_risk == 50_000
    assert 0.0 <= result.recovery_probability <= 1.0
    assert result.intervention_cost >= 0
    assert result.expected_recovery_value >= 0
    assert result.priority in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
    assert result.score_version == "v1"
    assert "hard" in result.scoring_reason
    assert "send_payment_link" in result.scoring_reason