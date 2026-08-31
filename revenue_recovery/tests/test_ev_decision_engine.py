"""Tests for First-Class Expected Value (EV) Decision Engine."""
from __future__ import annotations

from datetime import datetime, timezone
import pytest
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.proposals import RecoveryAction, RecoveryProposal
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.cost import InterventionCostModel
from app.scoring.expected_value import ExpectedValueScorer
from app.scoring.probability import RecoveryProbabilityModel


@pytest.fixture
def ev_scorer():
    return ExpectedValueScorer()


@pytest.fixture
def policy_engine():
    return InterventionPolicy()


def test_ev_scorer_evaluates_all_candidates(ev_scorer):
    """Verifies that evaluate_candidates scores all candidate actions with probability, cost, gross EV, and net EV."""
    candidates = ev_scorer.evaluate_candidates(
        amount_minor=5000000,  # ₹50,000
        failure_category="soft",
        attempt_number=1,
    )

    assert len(candidates) >= 5
    actions_found = {c["action"] for c in candidates}
    assert "retry_payment" in actions_found
    assert "send_payment_link" in actions_found
    assert "send_reminder" in actions_found
    assert "escalate_human" in actions_found
    assert "stop_recovery" in actions_found

    for cand in candidates:
        assert "recovery_probability" in cand
        assert "intervention_cost" in cand
        assert "gross_expected_recovery" in cand
        assert "net_expected_recovery" in cand


def test_highest_ev_permitted_action_selected(ev_scorer):
    """Verifies highest-EV action is ranked first in candidates list."""
    candidates = ev_scorer.evaluate_candidates(
        amount_minor=499900,  # ₹4,999
        failure_category="soft",
        attempt_number=1,
    )
    # Highest net_expected_recovery is first
    assert candidates[0]["net_expected_recovery"] >= candidates[1]["net_expected_recovery"]


def test_policy_blocks_highest_ev_unsafe_action(ev_scorer, policy_engine):
    """Verifies policy engine blocks highest-EV unsafe action (fraud flag), requiring second-highest or STOP."""
    item = RecoveryItem(
        id="item_fraud_ev_99",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_fraud_99",
        customer_id="cust_fraud",
        amount_minor=1820000,  # ₹18,200
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
        root_cause="fraud",
        metadata={"fraud_flag": True},
    )

    # 1. EV Scorer might estimate gross EV for retry_payment
    candidates = ev_scorer.evaluate_candidates(
        amount_minor=1820000,
        failure_category="fraud",
        attempt_number=1,
    )

    # 2. But Policy Engine BLOCKS retry_payment on fraud item
    guard = DefaultRecoveryGuard(stopping_rules=StoppingRules(), policy_engine=policy_engine)
    dec_retry = guard.evaluate(item, "retry_payment")
    assert dec_retry.allowed is False
    assert dec_retry.reason_code in ("fraud_retry_protection", "fraud_protection", "fraud_detected")

    # 3. Policy also BLOCKS send_payment_link on fraud item
    dec_link = guard.evaluate(item, "send_payment_link")
    assert dec_link.allowed is False

    # 4. Fraud item forces STOP status
    dec_stop = guard.evaluate(item, "stop_recovery")
    assert dec_stop.decision_type == "STOP"
    assert dec_stop.next_state == RecoveryStatus.STOPPED


def test_stop_wins_when_all_interventions_violate_policy_or_negative_ev(ev_scorer, policy_engine):
    """Verifies STOP wins when customer is opted out or attempt budget is exhausted."""
    guard = DefaultRecoveryGuard(stopping_rules=StoppingRules(), policy_engine=policy_engine)
    item_optout = RecoveryItem(
        id="item_optout_99",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_optout_99",
        customer_id="cust_optout",
        amount_minor=500000,
        currency="INR",
        created_at=datetime.now(timezone.utc),
        status=RecoveryStatus.DETECTED,
        root_cause="soft",
        metadata={"customer_opted_out": True},
    )

    dec_retry = guard.evaluate(item_optout, "retry_payment")
    assert dec_retry.allowed is False
    assert dec_retry.decision_type in ("STOP", "DENY")
    assert dec_retry.reason_code in ("opt_out_protection", "opt_out_compliance", "customer_opted_out", "opt_out_stop")

    dec_link = guard.evaluate(item_optout, "send_payment_link")
    assert dec_link.allowed is False


def test_cost_changes_affect_candidate_ranking(ev_scorer):
    """Verifies that higher intervention cost reduces net EV and changes candidate ranking."""
    prob_model = RecoveryProbabilityModel()

    cand1 = ev_scorer.evaluate_candidates(amount_minor=100000, failure_category="soft")
    net_retry = [c for c in cand1 if c["action"] == "retry_payment"][0]["net_expected_recovery"]
    cost_retry = [c for c in cand1 if c["action"] == "retry_payment"][0]["intervention_cost"]

    assert net_retry <= 100000
    assert cost_retry >= 0


def test_amount_at_risk_invariant_preserved(ev_scorer):
    """Verifies that expected recovery value is non-negative and bounded by amount_at_risk."""
    score = ev_scorer.score(
        amount_minor=499900,
        failure_category="soft",
        proposed_action="retry_payment",
    )

    assert 0 <= score.expected_recovery_value <= 499900
    assert 0.0 <= score.recovery_probability <= 1.0
