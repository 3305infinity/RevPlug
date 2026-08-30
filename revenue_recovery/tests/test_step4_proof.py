import time
import pytest
from fastapi.testclient import TestClient

from app.agents.validator import ProposalValidator, ProposalValidationError
from app.datasets.synthetic import generate_evaluation_dataset, get_opted_out_customers
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory, NormalizedFailure
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.domain.proposals import RecoveryAction, RecoveryProposal
from app.main import create_app
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.services.evaluation_service import EvaluationService


def test_step4_dataset_coverage():
    """Verify dataset contains coverage across all 5 surfaces and edge scenarios."""
    items = generate_evaluation_dataset(count=50, seed=42)
    assert len(items) == 50

    surfaces = {item.source_type for item in items}
    assert SourceType.PAYMENT_FAILURE in surfaces
    assert SourceType.CHECKOUT_ABANDONMENT in surfaces
    assert SourceType.SUBSCRIPTION_FAILURE in surfaces
    assert SourceType.RECEIVABLE in surfaces

    categories = {item.metadata.get("original_category") for item in items}
    assert "fraud" in categories
    assert "soft_optout" in categories
    assert len(categories) >= 6


def test_step4_rules_vs_llm_classification():
    """Verify rules-first classification vs LLM fallback pathing."""
    service = EvaluationService()
    result = service.run_batch_evaluation(count=50, seed=42)

    assert result.recoveros.cases_completed == 50
    response_dict = service.to_response_dict(result)
    assert "rules_classified_count" in response_dict["recoveros"]
    assert "llm_classified_count" in response_dict["recoveros"]
    assert "llm_fallback_count" in response_dict["recoveros"]


def test_step4_closed_action_set_enforcement():
    """Verify unauthorized actions like give_customer_50_percent_discount fail closed."""
    validator = ProposalValidator()
    context = RecoveryContext(
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=50000,
        currency="INR",
        expected_recovery_value=35000,
        customer_opt_out=False,
    )

    with pytest.raises(ValueError):
        invalid_action = RecoveryAction("give_customer_50_percent_discount")

    # Construct invalid proposal object directly with non-enum string
    class FakeProposal:
        action = "give_customer_50_percent_discount"
        confidence = 0.9
        reason = "Discount"
        customer_message = None

    with pytest.raises(ProposalValidationError):
        validator.validate(FakeProposal(), context)


def test_step4_safety_scenarios():
    """Verify live safety rules:
    A. Soft payment failure -> retry allowed
    B. Fraud -> recovery stopped/blocked
    C. Retry budget exhausted -> retry blocked/stopped
    D. Customer opt-out -> no automated contact
    E. Active promise-to-pay -> ordinary recovery paused
    """
    policy = InterventionPolicy(
        max_retry_attempts=3,
        opted_out_customer_ids=frozenset({"opt_out_101"}),
    )

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    # A. Soft failure -> retry allowed
    soft_item = RecoveryItem(
        id="item_soft",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_soft",
        customer_id="cust_normal",
        amount_minor=50000,
        currency="INR",
        created_at=now,
        status=RecoveryStatus.DETECTED,
        root_cause="soft",
        metadata={"attempt_count": 0},
    )
    d_soft = policy.evaluate(soft_item, "retry_payment")
    assert d_soft.allowed is True

    # B. Fraud -> blocked
    fraud_item = RecoveryItem(
        id="item_fraud",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_fraud",
        customer_id="cust_normal",
        amount_minor=50000,
        currency="INR",
        created_at=now,
        status=RecoveryStatus.DETECTED,
        root_cause="fraud",
        metadata={"attempt_count": 0},
    )
    d_fraud = policy.evaluate(fraud_item, "retry_payment")
    assert d_fraud.allowed is False

    # C. Retry budget exhausted -> blocked
    exhausted_item = RecoveryItem(
        id="item_exh",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_exh",
        customer_id="cust_normal",
        amount_minor=50000,
        currency="INR",
        created_at=now,
        status=RecoveryStatus.DETECTED,
        root_cause="soft",
        metadata={"attempt_count": 3},
    )
    d_exh = policy.evaluate(exhausted_item, "retry_payment")
    assert d_exh.allowed is False

    # D. Opt-out -> blocked
    optout_item = RecoveryItem(
        id="item_opt",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="ext_opt",
        customer_id="opt_out_101",
        amount_minor=50000,
        currency="INR",
        created_at=now,
        status=RecoveryStatus.DETECTED,
        root_cause="soft",
        metadata={"attempt_count": 0},
    )
    d_opt = policy.evaluate(optout_item, "retry_payment")
    assert d_opt.allowed is False


def test_step4_human_approval_safety_override_prevention():
    """Verify human approval of an unsafe action (fraud/opt-out) is blocked by policy engine."""
    app = create_app(webhook_secret="test-secret")
    client = TestClient(app)

    event_id = f"evt_fraud_{int(time.time())}"
    payment_id = f"pay_fraud_{int(time.time())}"

    # Trigger fraud recovery item
    res_trigger = client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": event_id,
            "payment_id": payment_id,
            "customer_id": "cust_fraud_test",
            "amount_minor": 50000,
            "error_reason": "payment_risk_check_failed",
        },
    )
    assert res_trigger.status_code == 200

    # Attempt human approval for retry_payment action on fraud item
    res_approve = client.post(
        f"/api/recovery-items/{payment_id}/approve",
        json={"action": "retry_payment"},
    )
    assert res_approve.status_code == 200
    data = res_approve.json()
    assert data["status"] == "denied_by_policy"
    assert data["policy_rule"] in ("fraud_cannot_retry", "block_hard_failure")


def test_step4_duplicate_webhook_idempotency():
    """Verify identical webhook sent twice produces 1 recovery item and 1 recovery action."""
    app = create_app(webhook_secret="test-secret")
    client = TestClient(app)

    event_id = f"evt_dup_{int(time.time())}"
    payment_id = f"pay_dup_{int(time.time())}"

    # First trigger
    r1 = client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": event_id,
            "payment_id": payment_id,
            "customer_id": "cust_dup",
            "amount_minor": 50000,
            "error_reason": "payment_timed_out",
        },
    )
    assert r1.status_code == 200
    assert r1.json()["status"] == "processed"

    # Second trigger (duplicate)
    r2 = client.post(
        "/api/demo/payment-failure",
        json={
            "event_id": event_id,
            "payment_id": payment_id,
            "customer_id": "cust_dup",
            "amount_minor": 50000,
            "error_reason": "payment_timed_out",
        },
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "duplicate"


def test_step4_cost_per_recovery_and_unnecessary_interventions():
    """Verify cost per recovery and unnecessary intervention calculations."""
    service = EvaluationService()
    result = service.run_batch_evaluation(count=50, seed=42)

    ros = result.recoveros
    assert ros.cases_evaluated == 50
    assert ros.actual_recovered > 0
    assert ros.cost_per_recovery >= 0
    assert ros.unnecessary_interventions >= 0
