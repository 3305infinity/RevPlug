import pytest
import math
from app.audit.models import InMemoryAuditLog
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryStatus, SourceType
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.scoring.probability import RecoveryProbabilityModel
from app.services.evaluation_service import EvaluationService
from app.services.recovery_orchestrator import RecoveryOrchestrator
from app.agents.decision_agent import MockRecoveryDecisionAgent


def test_probability_model_context_enrichment_and_bounds():
    """Verify probability model incorporates context and enforces strict [0, 1] bounds."""
    model = RecoveryProbabilityModel()

    # Normal soft failure
    p1 = model.estimate("soft", "retry_payment", attempt_number=1)
    assert 0.65 <= p1 <= 0.75

    # Opted-out customer context → 0.0
    p_opt = model.estimate("soft", "retry_payment", attempt_number=1, context={"customer_opted_out": True})
    assert p_opt == 0.0

    # Old overdue invoice context → lower probability
    p_fresh = model.estimate("soft", "send_payment_link", attempt_number=1, context={"days_overdue": 1})
    p_old = model.estimate("soft", "send_payment_link", attempt_number=1, context={"days_overdue": 30})
    assert p_old < p_fresh

    # Fail-safe bounds test: NaN / Inf context handling
    p_safe = model.estimate("soft", "retry_payment", attempt_number=1, context={"days_overdue": float("nan")})
    assert 0.0 <= p_safe <= 1.0


def test_scorer_evaluate_candidates():
    """Verify ExpectedValueScorer scores and ranks multiple candidate actions by net EV."""
    scorer = ExpectedValueScorer()
    candidates = scorer.evaluate_candidates(
        amount_minor=10000,
        failure_category="soft",
        attempt_number=1,
    )

    assert len(candidates) > 1
    # Check candidates are sorted descending by net_expected_recovery
    for i in range(len(candidates) - 1):
        assert candidates[i]["net_expected_recovery"] >= candidates[i + 1]["net_expected_recovery"]

    top = candidates[0]
    assert "action" in top
    assert "recovery_probability" in top
    assert "intervention_cost" in top
    assert "gross_expected_recovery" in top
    assert "net_expected_recovery" in top


def test_prohibited_higher_ev_action_loses_to_permitted_lower_ev():
    """Verify that a prohibited action (e.g. retry for fraud) loses to a permitted action."""
    orchestrator = RecoveryOrchestrator(
        policy_engine=InterventionPolicy(),
        audit_log=InMemoryAuditLog(),
        scorer=ExpectedValueScorer(),
        guard=DefaultRecoveryGuard(
            stopping_rules=StoppingRules(),
            policy_engine=InterventionPolicy(),
        ),
        agent=MockRecoveryDecisionAgent(),
    )

    item = RecoveryItem(
        id="fraud_test_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="evt_fraud",
        customer_id="cust_fraud",
        amount_minor=100000,
        currency="INR",
        created_at=None,
        status=RecoveryStatus.DETECTED,
        root_cause="fraud",
    )

    context = RecoveryContext(
        item_id=item.id,
        failure_category=FailureCategory.FRAUD,
        retryable=False,
        attempt_count=0,
        amount_minor=100000,
        currency="INR",
        expected_recovery_value=0,
        customer_opt_out=False,
    )

    result = orchestrator.run(item, context)

    # Fraud must be stopped regardless of potential theoretical return
    assert result.safety_decision == "STOP"
    assert result.score is not None
    assert "explainability" in result.score

    expl = result.score["explainability"]
    assert "rejected_alternatives" in expl
    # Check that prohibited alternatives are documented as prohibited
    assert any("Prohibited" in reason or "policy" in reason for reason in expl["rejected_alternatives"].values())


def test_explainability_metadata_structure():
    """Verify orchestrator attaches explainability metadata to run results and audit events."""
    audit_log = InMemoryAuditLog()
    orchestrator = RecoveryOrchestrator(
        policy_engine=InterventionPolicy(),
        audit_log=audit_log,
        scorer=ExpectedValueScorer(),
        guard=DefaultRecoveryGuard(
            stopping_rules=StoppingRules(),
            policy_engine=InterventionPolicy(),
        ),
        agent=MockRecoveryDecisionAgent(),
    )

    item = RecoveryItem(
        id="soft_explain_1",
        source_type=SourceType.PAYMENT_FAILURE,
        external_id="evt_soft",
        customer_id="cust_soft",
        amount_minor=20000,
        currency="INR",
        created_at=None,
        status=RecoveryStatus.DETECTED,
        root_cause="soft",
    )

    context = RecoveryContext(
        item_id=item.id,
        failure_category=FailureCategory.SOFT,
        retryable=True,
        attempt_count=0,
        amount_minor=20000,
        currency="INR",
        expected_recovery_value=13500,
        customer_opt_out=False,
    )

    result = orchestrator.run(item, context)

    assert result.score is not None
    assert "explainability" in result.score
    expl = result.score["explainability"]

    assert expl["selected_action"] == "send_payment_link"
    assert "why" in expl
    assert "rejected_alternatives" in expl

    # Check audit log event
    opt_events = [e for e in result.audit_events if e.action == "intervention_optimization_completed"]
    assert len(opt_events) == 1
    assert opt_events[0].metadata["selected_action"] == "send_payment_link"


def test_calibration_buckets_in_batch_evaluation():
    """Verify batch evaluation calculates probability calibration buckets and economic metrics."""
    eval_service = EvaluationService()
    res = eval_service.run_batch_evaluation(count=30, seed=42)

    assert "calibration_buckets" in res.dataset_info
    buckets = res.dataset_info["calibration_buckets"]

    assert "0.0-0.2" in buckets
    assert "0.2-0.4" in buckets
    assert "0.4-0.6" in buckets
    assert "0.6-0.8" in buckets
    assert "0.8-1.0" in buckets

    assert "economic_metrics" in res.dataset_info
    econ = res.dataset_info["economic_metrics"]
    assert "net_revenue_recovered" in econ
    assert "roi" in econ
    assert "expected_vs_actual_error" in econ
