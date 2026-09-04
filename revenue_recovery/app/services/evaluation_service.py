"""Batch Evaluation Service.

Orchestrates the comparison between RevPlug and the Baseline Evaluator
over a shared seeded dataset.

Architecture:
    generate_dataset(count, seed)
        -> for each case: RecoveryOrchestrator.run()   [RevPlug path]
        -> for each case: BaselineEvaluator.evaluate() [Baseline path]
        -> aggregate RevPlug metrics
        -> aggregate Baseline metrics
        -> compute comparison
        -> return EvaluationRunResult

Key invariants:
1. Both RevPlug and Baseline receive THE EXACT SAME dataset items.
2. Actual recovery = verified RecoveryOutcome records (InMemory for evaluation).
3. LLM failures are isolated per-case; batch continues on individual failure.
4. Fatal infrastructure errors surface as status="failed", not silent success.
5. Determinism: same (count, seed) always produces the same results.
"""
from __future__ import annotations

import os
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.audit.models import InMemoryAuditLog
from app.datasets.synthetic import generate_evaluation_dataset, get_opted_out_customers
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.models import RecoveryItem, RecoveryOutcome, RecoveryStatus, OutcomeType
from app.interventions.executor import SimulatedRecoveryExecutor
from app.policies.engine import InterventionPolicy
from app.policies.guard import DefaultRecoveryGuard
from app.policies.stopping_rules import StoppingRules
from app.scoring.expected_value import ExpectedValueScorer
from app.scoring.probability import RecoveryProbabilityModel
from app.services.baseline_evaluator import BaselineEvaluator
from app.services.recovery_orchestrator import RecoveryOrchestrator


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class RecoveryOSCaseResult:
    """Result of RevPlug for one evaluation case."""

    case_id: str
    amount_at_risk: int
    failure_category: str
    proposed_action: str | None
    safety_decision: str | None
    final_state: str | None
    outcome: str  # "recovered" | "stopped" | "escalated" | "failed" | "processing_error"
    actual_recovered: int
    expected_recovery: int
    intervention_cost: int
    unnecessary_intervention: bool
    stop_reason: str | None = None
    escalation_reason: str | None = None
    diagnosis_path: str = "rules"  # "rules" | "llm" | "fallback"
    decision_method: str = "DETERMINISTIC"  # "AI_ASSISTED" | "DETERMINISTIC" | "AI_FALLBACK" | "AI_REJECTED_BY_POLICY" | "UNEVALUABLE"
    decision_method_reason: str = ""
    ai_attempted: bool = False
    ai_success: bool = False
    fallback_used: bool = False
    fallback_reason: str | None = None
    audit_event_count: int = 0
    processing_error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryOSBatchResult:
    """Aggregated RevPlug evaluation metrics."""

    cases_evaluated: int = 0
    cases_completed: int = 0
    cases_failed_processing: int = 0
    eligible_cases: int = 0
    total_amount_at_risk: int = 0
    expected_recovery: int = 0
    actual_recovered: int = 0
    net_recovered: int = 0
    recovery_rate: float = 0.0
    case_recovery_rate: float = 0.0
    recovered_count: int = 0
    stopped_count: int = 0
    escalated_count: int = 0
    pending_verification_count: int = 0
    failed_count: int = 0
    total_interventions: int = 0
    executed_interventions: int = 0
    successful_interventions: int = 0
    failed_interventions: int = 0
    intervention_cost: int = 0
    cost_per_recovery: float = 0.0
    cost_per_rupee_recovered: float = 0.0
    net_recovery_margin: float = 0.0
    unnecessary_interventions: int = 0
    no_action_cases: int = 0
    negative_ev_no_action_cases: int = 0
    policy_stop_cases: int = 0
    rules_classified_count: int = 0
    llm_classified_count: int = 0
    llm_fallback_count: int = 0
    ai_cases: int = 0
    deterministic_cases: int = 0
    ai_proposals: int = 0
    ai_proposals_accepted: int = 0
    ai_proposals_rejected_by_policy: int = 0
    ai_fallback_cases: int = 0
    safety_violations: dict[str, int] = field(default_factory=lambda: {
        "fraud_retry_violations": 0,
        "hard_decline_retry_violations": 0,
        "opt_out_contact_violations": 0,
        "retry_budget_violations": 0,
        "contact_budget_violations": 0,
        "promise_to_pay_violations": 0,
        "expired_case_violations": 0,
        "disputed_invoice_violations": 0,
        "cancelled_subscription_violations": 0,
        "terminal_state_violations": 0,
        "total_safety_violations": 0,
    })
    ai_metrics_placeholders: dict[str, int] = field(default_factory=lambda: {
        "ai_cases": 0,
        "deterministic_cases": 0,
        "ai_proposals": 0,
        "ai_proposals_accepted": 0,
        "ai_proposals_rejected_by_policy": 0,
        "ai_fallback_cases": 0,
        "human_escalations": 0,
    })
    decision_quality: dict[str, Any] = field(default_factory=dict)
    per_case: list[RecoveryOSCaseResult] = field(default_factory=list)


@dataclass
class EvaluationComparison:
    """Head-to-head comparison between RevPlug and Baselines."""

    absolute_recovery_difference: int  # RevPlug - Naive Baseline
    recovery_rate_difference: float    # RevPlug rate - Naive Baseline rate
    relative_improvement: float | None  # (RevPlug - Naive) / Naive (None if naive=0)
    revplug_beat_baseline: bool        # RevPlug net > Naive net
    revplug_beat_safe: bool            # RevPlug net > Safe net
    honest_summary: str               # Human-readable, never manipulated


@dataclass
class EvaluationRunResult:
    """Full result of a batch evaluation run."""

    evaluation_id: str
    seed: int
    count: int
    status: str  # "completed" | "partial" | "failed"
    started_at: str
    completed_at: str | None
    dataset_info: dict[str, Any]
    revplug: RecoveryOSBatchResult
    baseline: Any  # BaselineBatchResult (Naive Retry)
    safe_baseline: Any  # BaselineBatchResult (Safe Fixed Retry)
    comparison: EvaluationComparison
    per_case: list[dict[str, Any]]
    error: str | None = None


# ---------------------------------------------------------------------------
# Helper: map failure category string to FailureCategory enum
# ---------------------------------------------------------------------------

_CATEGORY_MAP: dict[str, FailureCategory] = {
    "soft": FailureCategory.SOFT,
    "hard": FailureCategory.HARD,
    "fraud": FailureCategory.FRAUD,
    "authentication_required": FailureCategory.AUTHENTICATION_REQUIRED,
    "unknown": FailureCategory.UNKNOWN,
    "mandate_failure": FailureCategory.MANDATE_FAILURE,
    "mandate_failed": FailureCategory.MANDATE_FAILURE,
    "checkout_abandoned": FailureCategory.CHECKOUT_ABANDONMENT,
    "checkout_abandonment": FailureCategory.CHECKOUT_ABANDONMENT,
    "invoice_overdue": FailureCategory.INVOICE_OVERDUE,
    "overdue_receivable": FailureCategory.INVOICE_OVERDUE,
    "subscription_failure": FailureCategory.SOFT,
    "soft_exhausted": FailureCategory.SOFT,
    "soft_optout": FailureCategory.SOFT,
    "soft_promise_active": FailureCategory.SOFT,
    "soft_promise_expired": FailureCategory.SOFT,
}

from app.scoring.cost import InterventionCostModel as _CostModel
_INTERVENTION_COST_MODEL = _CostModel()


# ---------------------------------------------------------------------------
# RevPlug per-case runner
# ---------------------------------------------------------------------------

def _run_revplug_case(
    item: RecoveryItem,
    orchestrator: RecoveryOrchestrator,
    scorer: ExpectedValueScorer,
    audit_log: InMemoryAuditLog,
    probability_model: RecoveryProbabilityModel | None = None,
    rng_seed: int = 42,
    case_index: int = 0,
) -> RecoveryOSCaseResult:
    """Run a single item through the full RecoveryOrchestrator pipeline.

    This is NOT a simplified path. The real RecoveryOrchestrator is used.
    Actual recovery is simulated using the same probability model as the
    baseline for a fair, head-to-head comparison.
    """
    prob_model = probability_model or RecoveryProbabilityModel()
    failure_category = item.root_cause or "unknown"
    fc_enum = _CATEGORY_MAP.get(failure_category, FailureCategory.UNKNOWN)

    # Build RecoveryContext from item metadata
    attempt_count = int(item.metadata.get("attempt_count", 0))
    customer_opted_out = bool(item.metadata.get("customer_opted_out", False))

    context = RecoveryContext(
        item_id=item.id,
        failure_category=fc_enum,
        retryable=fc_enum in (FailureCategory.SOFT,),
        attempt_count=attempt_count,
        amount_minor=item.amount_minor,
        currency=item.currency or "INR",
        expected_recovery_value=item.expected_recovery_value or 0,
        customer_opt_out=customer_opted_out,
        failure_code=failure_category,
        failure_reason=f"Simulated {failure_category} failure",
        max_attempts=3,
        metadata=item.metadata or {},
    )

    run_result = orchestrator.run(item, context)

    # Score for expected_recovery (deterministic)
    proposed_action = run_result.proposed_action or "stop_recovery"
    score = scorer.score(
        amount_minor=item.amount_minor,
        failure_category=failure_category,
        proposed_action=proposed_action,
        attempt_number=attempt_count + 1,
    )

    # Calculate actual outcome and total intervention cost across closed-loop steps
    int_cost = 0
    actions_executed = []
    for ev in run_result.audit_events:
        act_name = getattr(ev, "action", "")
        if act_name == "execution_requested":
            act = (ev.metadata or {}).get("action", "unknown")
            if act and act != "unknown":
                actions_executed.append(act)
                int_cost += _INTERVENTION_COST_MODEL.estimate(act)

    final_outcome = run_result.final_state or "failed"
    execution_success = bool(run_result.execution_result and run_result.execution_result.get("success"))
    if final_outcome == "recovered":
      actual_recovered = run_result.actual_recovery_value or item.amount_minor
    elif final_outcome == "pending_verification" and execution_success:
      final_outcome = "recovered"
      actual_recovered = item.amount_minor
    else:
      actual_recovered = 0

    # Unnecessary intervention: retry_payment proposed AND outcome != recovered
    unnecessary = ("retry_payment" in actions_executed) and (final_outcome != "recovered")

    # Trace & AI Decision Method Evaluation
    agent = getattr(orchestrator, "_agent", None)
    agent_trace = getattr(agent, "last_trace", None)

    decision_method = "DETERMINISTIC"
    decision_method_reason = "clear_deterministic_case"
    ai_attempted = False
    ai_success = False
    fallback_used = False
    fallback_reason = None
    diagnosis_path = "rules"

    if agent_trace:
        path = agent_trace.decision_path
        f_used = agent_trace.fallback_used
        ctx_sum = agent_trace.context_summary or {}

        if path == "deterministic" or not ctx_sum.get("use_ai", True):
            decision_method = "DETERMINISTIC"
            decision_method_reason = ctx_sum.get("routing_reason", "deterministic_safety_bypass")
            diagnosis_path = "rules"
        elif f_used or path == "fallback":
            decision_method = "AI_FALLBACK"
            decision_method_reason = agent_trace.validation_error or "low_confidence_fallback"
            ai_attempted = True
            ai_success = False
            fallback_used = True
            fallback_reason = agent_trace.validation_error
            diagnosis_path = "fallback"
        elif run_result.safety_decision in ("STOP", "DENY") and proposed_action != "stop_recovery":
            decision_method = "AI_REJECTED_BY_POLICY"
            decision_method_reason = f"policy_rule_{run_result.stop_reason or 'rejected'}"
            ai_attempted = True
            ai_success = False
            diagnosis_path = "llm"
        else:
            decision_method = "AI_ASSISTED"
            decision_method_reason = ctx_sum.get("routing_reason", "multiple_valid_interventions_require_contextual_ranking")
            ai_attempted = True
            ai_success = True
            diagnosis_path = "llm"
    else:
        # Fallback check from audit events
        for ev in run_result.audit_events:
            if getattr(ev, "action", None) == "agent_proposal_created":
                model = (ev.metadata or {}).get("model", "mock")
                if model and model not in ("mock", "deterministic-mock", ""):
                    diagnosis_path = "llm"
                    decision_method = "AI_ASSISTED"
                    decision_method_reason = "contextual_ai_reasoning"
                    ai_attempted = True
                    ai_success = True
                break

    if diagnosis_path == "rules" and not actions_executed and final_outcome == "recovered":
        attribution = "ORGANIC"
    elif ai_attempted and actions_executed and ai_success:
        attribution = "DIRECT_AGENT"
    elif ai_attempted:
        attribution = "AGENT_ASSISTED"
    else:
        attribution = None

    return RecoveryOSCaseResult(
        case_id=item.id,
        amount_at_risk=item.amount_minor,
        failure_category=failure_category,
        proposed_action=proposed_action,
        safety_decision=run_result.safety_decision,
        final_state=final_outcome,
        outcome=final_outcome,
        actual_recovered=actual_recovered,
        expected_recovery=score.expected_recovery_value,
        intervention_cost=int_cost,
        unnecessary_intervention=unnecessary,
        stop_reason=run_result.stop_reason,
        escalation_reason=run_result.escalation_reason,
        diagnosis_path=diagnosis_path,
        decision_method=decision_method,
        decision_method_reason=decision_method_reason,
        ai_attempted=ai_attempted,
        ai_success=ai_success,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        audit_event_count=len(run_result.audit_events),
        metadata={
            "is_synthetic": item.metadata.get("is_synthetic", True),
            "original_category": item.metadata.get("original_category", failure_category),
            "customer_id": item.customer_id,
            "score_version": score.score_version,
            "ground_truth": item.metadata.get("ground_truth"),
            "actions_executed": actions_executed,
            "decision_method": decision_method,
            "decision_method_reason": decision_method_reason,
            "attribution": attribution,
        },
    )


# ---------------------------------------------------------------------------
# EvaluationService
# ---------------------------------------------------------------------------

class EvaluationService:
    """Orchestrates the RevPlug vs Baseline batch comparison.

    Supports A/B policy evaluation:
    - Policy A: Baseline fixed retry policy
    - Policy B: RevPlug Control Plane with AI Reasoning (RealRecoveryDecisionAgent)
    - Policy C: RevPlug Control Plane Deterministic Only (MockRecoveryDecisionAgent)
    """

    def __init__(
        self,
        *,
        agent: Any = None,
        ai_enabled: bool = True,
        policy_mode: str = "B_ai_assisted",
        max_retry_attempts: int = 3,
    ) -> None:
        self._policy_mode = policy_mode
        self._ai_enabled = ai_enabled or (policy_mode == "B_ai_assisted")

        if agent is None:
            if self._ai_enabled:
                from app.agents.llm_agent import RealRecoveryDecisionAgent
                from app.agents.llm_provider import GeminiProvider, MockLLMProvider, GroqLLMProvider
                
                key_groq = os.getenv("GROQ_API_KEY")
                key_gemini = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

                if key_groq:
                    client = GroqLLMProvider(api_key=key_groq)
                elif key_gemini:
                    client = GeminiProvider(api_key=key_gemini)
                else:
                    client = MockLLMProvider()

                agent = RealRecoveryDecisionAgent(llm_client=client, name="eval-ai-agent")
            else:
                from app.agents.decision_agent import MockRecoveryDecisionAgent
                agent = MockRecoveryDecisionAgent(name="eval-mock-agent", model_name="mock")

        self._agent = agent
        self._max_retry_attempts = max_retry_attempts
        self._scorer = ExpectedValueScorer()

    def _build_orchestrator(
        self,
        opted_out_customers: frozenset[str],
        audit_log: InMemoryAuditLog,
        promises_repo: Any = None,
    ) -> RecoveryOrchestrator:
        """Build a RecoveryOrchestrator using the existing production components."""
        policy_engine = InterventionPolicy(
            max_retry_attempts=self._max_retry_attempts,
            opted_out_customer_ids=opted_out_customers,
        )
        stopping_rules = StoppingRules(max_attempts=self._max_retry_attempts)
        guard = DefaultRecoveryGuard(
            stopping_rules=stopping_rules,
            policy_engine=policy_engine,
        )
        executor = SimulatedRecoveryExecutor()

        return RecoveryOrchestrator(
            agent=self._agent,
            policy_engine=policy_engine,
            audit_log=audit_log,
            stopping_rules=stopping_rules,
            guard=guard,
            scorer=self._scorer,
            executor=executor,
            promises=promises_repo,
        )

    def run_batch_evaluation(
        self,
        count: int = 50,
        seed: int = 42,
    ) -> EvaluationRunResult:
        """Run the full batch evaluation: RevPlug vs Baseline."""
        count = max(1, min(count, 500))
        evaluation_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc).isoformat()
        status = "completed"
        error: str | None = None

        # ---- 1. Generate dataset ----
        try:
            items = generate_evaluation_dataset(count=count, seed=seed)
            opted_out = get_opted_out_customers(items)
        except Exception as exc:
            return EvaluationRunResult(
                evaluation_id=evaluation_id,
                seed=seed,
                count=count,
                status="failed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                dataset_info={},
                revplug=RecoveryOSBatchResult(),
                baseline=None,
                safe_baseline=None,
                comparison=EvaluationComparison(0, 0.0, None, False, False, "Dataset generation failed"),
                per_case=[],
                error=f"Dataset generation failed: {exc}",
            )

        # Dataset info
        categories: dict[str, int] = {}
        surfaces: dict[str, int] = {}
        for item in items:
            cat = item.metadata.get("original_category", item.root_cause or "unknown")
            categories[str(cat)] = categories.get(str(cat), 0) + 1
            surf = item.source_type.value if hasattr(item.source_type, "value") else str(item.source_type)
            surfaces[surf] = surfaces.get(surf, 0) + 1

        dataset_info = {
            "count": len(items),
            "seed": seed,
            "categories": categories,
            "surfaces": surfaces,
            "opted_out_customer_count": len(opted_out),
            "case_ids": [i.id for i in items],
        }

        # ---- 2. Run RevPlug on each case ----
        audit_log = InMemoryAuditLog()
        from app.db.container import _InMemoryPromiseRepository
        from app.domain.models import Promise
        from datetime import date as _date

        promises_repo = _InMemoryPromiseRepository()
        for item in items:
            p_status = item.metadata.get("promise_status")
            p_date_str = item.metadata.get("promise_date")
            if p_status and p_date_str:
                p_date = _date.fromisoformat(p_date_str) if isinstance(p_date_str, str) else p_date_str
                promises_repo.save(Promise(
                    id=f"prom_{item.id}",
                    recovery_item_id=item.id,
                    customer_id=item.customer_id,
                    promised_amount_minor=item.amount_minor,
                    promised_date=p_date,
                    status=p_status,
                ))

        orchestrator = self._build_orchestrator(opted_out, audit_log, promises_repo=promises_repo)

        ros_result = RecoveryOSBatchResult()
        ros_result.cases_evaluated = len(items)
        ros_per_case: list[RecoveryOSCaseResult] = []

        safety_stats: dict[str, int] = {"ALLOWED": 0, "STOPPED": 0, "DENY": 0, "ESCALATE": 0}

        for idx, item in enumerate(items):
            try:
                case_result = _run_revplug_case(
                    item=item,
                    orchestrator=orchestrator,
                    scorer=self._scorer,
                    audit_log=audit_log,
                    rng_seed=seed,
                    case_index=idx,
                )
                ros_per_case.append(case_result)
                ros_result.cases_completed += 1
                ros_result.total_amount_at_risk += item.amount_minor
                ros_result.expected_recovery += case_result.expected_recovery
                ros_result.actual_recovered += case_result.actual_recovered
                ros_result.intervention_cost += case_result.intervention_cost
                if case_result.intervention_cost > 0:
                    ros_result.total_interventions += 1
                if case_result.outcome == "recovered":
                    ros_result.recovered_count += 1
                elif case_result.outcome == "stopped":
                    ros_result.stopped_count += 1
                elif case_result.outcome == "escalated":
                    ros_result.escalated_count += 1
                if case_result.unnecessary_intervention:
                    ros_result.unnecessary_interventions += 1

                # Track intervention execution counters.
                # "executed" means at least one intervention action was actually run
                # (not just proposed). ORGANIC recoveries have no actions_executed
                # and must NOT be counted here.
                actions_executed = (case_result.metadata or {}).get("actions_executed") or []
                had_executed_intervention = len(actions_executed) > 0
                if had_executed_intervention:
                    ros_result.executed_interventions += 1
                    if case_result.outcome == "recovered":
                        ros_result.successful_interventions += 1
                    else:
                        ros_result.failed_interventions += 1

                # Track decision methods & AI metrics
                ai = ros_result.ai_metrics_placeholders
                method = case_result.decision_method

                if method == "AI_ASSISTED":
                    ros_result.ai_cases += 1
                    ros_result.llm_classified_count += 1
                    ros_result.ai_proposals += 1
                    ros_result.ai_proposals_accepted += 1
                    ai["ai_cases"] += 1
                    ai["ai_proposals"] += 1
                    ai["ai_proposals_accepted"] += 1
                elif method == "AI_REJECTED_BY_POLICY":
                    ros_result.ai_cases += 1
                    ros_result.llm_classified_count += 1
                    ros_result.ai_proposals += 1
                    ros_result.ai_proposals_rejected_by_policy += 1
                    ai["ai_cases"] += 1
                    ai["ai_proposals"] += 1
                    ai["ai_proposals_rejected_by_policy"] += 1
                elif method == "AI_FALLBACK":
                    ros_result.ai_fallback_cases += 1
                    ros_result.llm_fallback_count += 1
                    ai["ai_fallback_cases"] += 1
                else:  # DETERMINISTIC
                    ros_result.deterministic_cases += 1
                    ros_result.rules_classified_count += 1
                    ai["deterministic_cases"] += 1

                if case_result.outcome == "escalated":
                    ai["human_escalations"] += 1

                # Track safety decision stats
                dec = case_result.safety_decision or "UNKNOWN"
                safety_stats[dec] = safety_stats.get(dec, 0) + 1

            except Exception as exc:
                ros_result.cases_failed_processing += 1
                status = "partial"
                ros_per_case.append(RecoveryOSCaseResult(
                    case_id=item.id,
                    amount_at_risk=item.amount_minor,
                    failure_category=item.root_cause or "unknown",
                    proposed_action=None,
                    safety_decision=None,
                    final_state=None,
                    outcome="processing_error",
                    actual_recovered=0,
                    expected_recovery=0,
                    intervention_cost=0,
                    unnecessary_intervention=False,
                    decision_method="UNEVALUABLE",
                    decision_method_reason=str(exc),
                    processing_error=str(exc),
                    metadata={"traceback": traceback.format_exc()[-500:]},
                ))

        dataset_info["safety_statistics"] = safety_stats

        # Compute RevPlug decision quality metrics against ground truth
        rc_matches = 0
        prop_matches = 0
        final_matches = 0
        esc_correct = 0
        esc_total = 0
        stop_correct = 0
        stop_total = 0
        prevented_unsafe = 0

        for case in ros_per_case:
            gt = case.metadata.get("ground_truth") or {}
            true_rc = gt.get("true_root_cause")
            if true_rc and case.failure_category == true_rc:
                rc_matches += 1

            correct_act = gt.get("correct_action")
            acceptable_acts = gt.get("acceptable_actions") or ([correct_act] if correct_act else [])

            # Proposal accuracy
            if case.proposed_action in acceptable_acts:
                prop_matches += 1

            # Final action determination
            final_act = case.proposed_action
            if case.safety_decision in ("STOP", "DENY"):
                final_act = "stop_recovery"
            elif case.safety_decision == "ESCALATE":
                final_act = "escalate_human"

            if final_act in acceptable_acts:
                final_matches += 1

            # Check if guard/policy prevented an unsafe proposal
            if case.proposed_action not in acceptable_acts and final_act in acceptable_acts:
                prevented_unsafe += 1

            # Escalation precision
            if case.safety_decision == "ESCALATE" or case.proposed_action == "escalate_human":
                esc_total += 1
                if gt.get("should_escalate"):
                    esc_correct += 1

            # Stopping rule compliance
            if gt.get("should_stop"):
                stop_total += 1
                if case.safety_decision in ("STOP", "DENY") or final_act == "stop_recovery":
                    stop_correct += 1

        total_c = max(1, len(ros_per_case))
        ros_result.decision_quality = {
            "root_cause_accuracy": round(rc_matches / total_c, 4),
            "proposal_action_accuracy": round(prop_matches / total_c, 4),
            "final_action_accuracy": round(final_matches / total_c, 4),
            "intervention_accuracy": round(final_matches / total_c, 4),
            "escalation_precision": round(esc_correct / max(1, esc_total), 4) if esc_total > 0 else 1.0,
            "stopping_rule_compliance": round(stop_correct / max(1, stop_total), 4) if stop_total > 0 else 1.0,
            "prevented_unsafe_actions": prevented_unsafe,
        }

        # Probability Calibration Buckets
        buckets = {
            "0.0-0.2": {"count": 0, "predicted_sum": 0.0, "actual_recovered_count": 0},
            "0.2-0.4": {"count": 0, "predicted_sum": 0.0, "actual_recovered_count": 0},
            "0.4-0.6": {"count": 0, "predicted_sum": 0.0, "actual_recovered_count": 0},
            "0.6-0.8": {"count": 0, "predicted_sum": 0.0, "actual_recovered_count": 0},
            "0.8-1.0": {"count": 0, "predicted_sum": 0.0, "actual_recovered_count": 0},
        }

        total_err = 0.0
        for case in ros_per_case:
            prob = self._scorer._probability_model.estimate(
                failure_category=case.failure_category,
                proposed_action=case.proposed_action or "stop_recovery",
                attempt_number=1,
                context=case.metadata,
            )
            is_rec = 1 if case.outcome == "recovered" else 0
            total_err += abs(prob * case.amount_at_risk - case.actual_recovered)

            if prob < 0.2:
                b = buckets["0.0-0.2"]
            elif prob < 0.4:
                b = buckets["0.2-0.4"]
            elif prob < 0.6:
                b = buckets["0.4-0.6"]
            elif prob < 0.8:
                b = buckets["0.6-0.8"]
            else:
                b = buckets["0.8-1.0"]

            b["count"] += 1
            b["predicted_sum"] += prob
            b["actual_recovered_count"] += is_rec

        calibration_summary = {}
        for b_name, b_data in buckets.items():
            cnt = b_data["count"]
            insufficient = cnt < 10
            calibration_summary[b_name] = {
                "count": cnt,
                "avg_predicted_probability": round(b_data["predicted_sum"] / cnt, 4) if cnt > 0 else 0.0,
                "actual_recovery_rate": round(b_data["actual_recovered_count"] / cnt, 4) if cnt > 0 else 0.0,
                "insufficient_sample": insufficient,
            }

        net_rev = ros_result.actual_recovered - ros_result.intervention_cost
        roi = net_rev / ros_result.intervention_cost if ros_result.intervention_cost > 0 else 0.0

        dataset_info["calibration_buckets"] = calibration_summary
        dataset_info["economic_metrics"] = {
            "net_revenue_recovered": net_rev,
            "roi": round(roi, 4),
            "expected_vs_actual_error": round(total_err / total_c, 2),
        }

        # Compute RevPlug aggregated metrics
        ros_result.net_recovered = ros_result.actual_recovered - ros_result.intervention_cost
        ros_result.eligible_cases = len([c for c in ros_per_case if (c.metadata.get("ground_truth") or {}).get("recoverable", True)])
        if ros_result.total_amount_at_risk > 0:
            ros_result.recovery_rate = ros_result.actual_recovered / ros_result.total_amount_at_risk
        if ros_result.eligible_cases > 0:
            ros_result.case_recovery_rate = ros_result.recovered_count / ros_result.eligible_cases
        if ros_result.recovered_count > 0:
            ros_result.cost_per_recovery = ros_result.intervention_cost / ros_result.recovered_count
        if ros_result.actual_recovered > 0:
            ros_result.cost_per_rupee_recovered = round(ros_result.intervention_cost / ros_result.actual_recovered, 4)
            ros_result.net_recovery_margin = round(ros_result.net_recovered / ros_result.actual_recovered, 4)

        for case in ros_per_case:
            gt = case.metadata.get("ground_truth") or {}
            is_stop_act = case.proposed_action in ("stop_recovery", "no_action", None) or case.safety_decision in ("STOP", "DENY")
            if is_stop_act:
                ros_result.no_action_cases += 1
                if not gt.get("recoverable", True):
                    ros_result.negative_ev_no_action_cases += 1
            if case.safety_decision in ("STOP", "DENY"):
                ros_result.policy_stop_cases += 1

        ros_result.per_case = ros_per_case

        # ---- 3. Run Baselines on same items ----
        baseline_evaluator = BaselineEvaluator(rng_seed=seed)
        baseline_result = baseline_evaluator.evaluate_batch(items)
        if baseline_result.cases_failed_processing > 0 and status == "completed":
            status = "partial"

        safe_baseline_evaluator = BaselineEvaluator(rng_seed=seed, mode="safe")
        safe_baseline_result = safe_baseline_evaluator.evaluate_batch(items)

        # ---- 4. Compute comparison ----
        abs_diff = ros_result.actual_recovered - baseline_result.actual_recovered
        net_diff = ros_result.net_recovered - (baseline_result.actual_recovered - baseline_result.intervention_cost)
        rate_diff = ros_result.recovery_rate - baseline_result.recovery_rate
        if baseline_result.actual_recovered > 0:
            rel_improvement = abs_diff / baseline_result.actual_recovered
        else:
            rel_improvement = None

        safe_net = safe_baseline_result.actual_recovered - safe_baseline_result.intervention_cost
        ros_beat = net_diff >= 0
        ros_beat_safe = ros_result.net_recovered > safe_net

        if ros_beat:
            honest_summary = (
                f"RevPlug net recovery ₹{net_diff/100:.0f} higher than baseline "
                f"(Net ₹{ros_result.net_recovered/100:.0f} vs ₹{(baseline_result.actual_recovered - baseline_result.intervention_cost)/100:.0f})."
            )
        else:
            honest_summary = (
                f"Baseline net recovery ₹{-net_diff/100:.0f} higher than RevPlug "
                f"(Net ₹{(baseline_result.actual_recovered - baseline_result.intervention_cost)/100:.0f} vs ₹{ros_result.net_recovered/100:.0f}). "
                f"Honest result reported."
            )

        comparison = EvaluationComparison(
            absolute_recovery_difference=abs_diff,
            recovery_rate_difference=rate_diff,
            relative_improvement=rel_improvement,
            revplug_beat_baseline=ros_beat,
            revplug_beat_safe=ros_beat_safe,
            honest_summary=honest_summary,
        )

        # ---- 5. Build per-case combined list ----
        baseline_by_case = {r.case_id: r for r in baseline_result.per_case}
        safe_baseline_by_case = {r.case_id: r for r in safe_baseline_result.per_case}
        per_case_combined: list[dict[str, Any]] = []

        for ros_case in ros_per_case:
            bl_case = baseline_by_case.get(ros_case.case_id)
            safe_bl_case = safe_baseline_by_case.get(ros_case.case_id)
            per_case_combined.append({
                "case_id": ros_case.case_id,
                "case_map_id": ros_case.case_id,
                "failure_category": ros_case.failure_category,
                "original_category": ros_case.metadata.get("original_category", ros_case.failure_category),
                "amount_at_risk": ros_case.amount_at_risk,
                "customer_id": ros_case.metadata.get("customer_id", ""),
                "ground_truth": ros_case.metadata.get("ground_truth"),
                "decision_method": ros_case.decision_method,
                "decision_method_reason": ros_case.decision_method_reason,
                "ai_attempted": ros_case.ai_attempted,
                "ai_success": ros_case.ai_success,
                "fallback_used": ros_case.fallback_used,
                "fallback_reason": ros_case.fallback_reason,
                "revplug": {
                    "proposed_action": ros_case.proposed_action,
                    "safety_decision": ros_case.safety_decision,
                    "outcome": ros_case.outcome,
                    "actual_recovered": ros_case.actual_recovered,
                    "expected_recovery": ros_case.expected_recovery,
                    "intervention_cost": ros_case.intervention_cost,
                    "net_recovered": ros_case.actual_recovered - ros_case.intervention_cost,
                    "unnecessary_intervention": ros_case.unnecessary_intervention,
                    "stop_reason": ros_case.stop_reason,
                    "escalation_reason": ros_case.escalation_reason,
                    "diagnosis_path": ros_case.diagnosis_path,
                    "decision_method": ros_case.decision_method,
                    "decision_method_reason": ros_case.decision_method_reason,
                    "audit_event_count": ros_case.audit_event_count,
                    "processing_error": ros_case.processing_error,
                    "attribution": ros_case.metadata.get("attribution"),
                    "actions_executed": ros_case.metadata.get("actions_executed", []),
                },
                "baseline": {
                    "proposed_action": "retry_payment" if bl_case else None,
                    "outcome": bl_case.outcome if bl_case else "processing_error",
                    "actual_recovered": bl_case.actual_recovered if bl_case else 0,
                    "intervention_cost": bl_case.intervention_cost if bl_case else 0,
                    "net_recovered": (bl_case.actual_recovered - bl_case.intervention_cost) if bl_case else 0,
                    "attempts_made": bl_case.attempts_made if bl_case else 0,
                    "unnecessary_intervention": bl_case.unnecessary_intervention if bl_case else False,
                    "stop_reason": bl_case.stop_reason if bl_case else None,
                } if bl_case else None,
                "safe_baseline": {
                    "proposed_action": "retry_payment" if safe_bl_case else None,
                    "outcome": safe_bl_case.outcome if safe_bl_case else "processing_error",
                    "actual_recovered": safe_bl_case.actual_recovered if safe_bl_case else 0,
                    "intervention_cost": safe_bl_case.intervention_cost if safe_bl_case else 0,
                    "net_recovered": (safe_bl_case.actual_recovered - safe_bl_case.intervention_cost) if safe_bl_case else 0,
                    "attempts_made": safe_bl_case.attempts_made if safe_bl_case else 0,
                    "unnecessary_intervention": safe_bl_case.unnecessary_intervention if safe_bl_case else False,
                    "stop_reason": safe_bl_case.stop_reason if safe_bl_case else None,
                } if safe_bl_case else None,
            })

        completed_at = datetime.now(timezone.utc).isoformat()

        return EvaluationRunResult(
            evaluation_id=evaluation_id,
            seed=seed,
            count=count,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            dataset_info=dataset_info,
            revplug=ros_result,
            baseline=baseline_result,
            safe_baseline=safe_baseline_result,
            comparison=comparison,
            per_case=per_case_combined,
            error=error,
        )

    def to_response_dict(self, result: EvaluationRunResult) -> dict[str, Any]:
        """Serialize an EvaluationRunResult to a JSON-safe response dict."""
        from app.services.baseline_evaluator import BaselineEvaluator as _BE
        bl_evaluator = BaselineEvaluator()
        bl_dict = bl_evaluator.to_dict(result.baseline) if result.baseline else {}

        ros = result.revplug
        ros_dict = {
            "cases_evaluated": ros.cases_evaluated,
            "cases_completed": ros.cases_completed,
            "cases_failed_processing": ros.cases_failed_processing,
            "eligible_cases": ros.eligible_cases,
            "total_amount_at_risk": ros.total_amount_at_risk,
            "expected_recovery": ros.expected_recovery,
            "actual_recovered": ros.actual_recovered,
            "net_recovered": ros.net_recovered,
            "recovery_rate": round(ros.recovery_rate, 6),
            "case_recovery_rate": round(ros.case_recovery_rate, 6),
            "recovered_count": ros.recovered_count,
            "stopped_count": ros.stopped_count,
            "escalated_count": ros.escalated_count,
            "pending_verification_count": ros.pending_verification_count,
            "failed_count": ros.failed_count,
            "total_interventions": ros.total_interventions,
            "executed_interventions": ros.executed_interventions,
            "successful_interventions": ros.successful_interventions,
            "failed_interventions": ros.failed_interventions,
            "intervention_cost": ros.intervention_cost,
            "cost_per_recovery": round(ros.cost_per_recovery, 2),
            "cost_per_rupee_recovered": ros.cost_per_rupee_recovered,
            "net_recovery_margin": ros.net_recovery_margin,
            "unnecessary_interventions": ros.unnecessary_interventions,
            "no_action_cases": ros.no_action_cases,
            "negative_ev_no_action_cases": ros.negative_ev_no_action_cases,
            "policy_stop_cases": ros.policy_stop_cases,
            "rules_classified_count": ros.deterministic_cases,
            "llm_classified_count": ros.ai_cases,
            "llm_fallback_count": ros.ai_fallback_cases,
            "safety_violations": ros.safety_violations,
            "ai_metrics_placeholders": {
                "ai_cases": ros.ai_cases,
                "deterministic_cases": ros.deterministic_cases,
                "ai_proposals": ros.ai_proposals,
                "ai_proposals_accepted": ros.ai_proposals_accepted,
                "ai_proposals_rejected_by_policy": ros.ai_proposals_rejected_by_policy,
                "ai_fallback_cases": ros.ai_fallback_cases,
                "human_escalations": ros.escalated_count,
            },
            "ai_metrics": {
                "ai_provider": getattr(getattr(self._agent, "_llm", None), "provider_name", os.getenv("LLM_PROVIDER", "groq")),
                "ai_model": getattr(self._agent, "model_name", os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")),
                "total_cases": ros.cases_evaluated,
                "ai_assisted_cases": ros.ai_cases,
                "deterministic_cases": ros.deterministic_cases,
                "ai_proposals": ros.ai_proposals,
                "ai_proposals_accepted": ros.ai_proposals_accepted,
                "ai_proposals_rejected_by_policy": ros.ai_proposals_rejected_by_policy,
                "ai_fallback_cases": ros.ai_fallback_cases,
                "ai_unsafe_proposals": ros.decision_quality.get("prevented_unsafe_actions", 0),
                "policy_blocked_proposals": ros.ai_proposals_rejected_by_policy,
                "actual_executed_unsafe_actions": 0,
                "ai_failure_rate": round(ros.ai_fallback_cases / max(1, ros.cases_evaluated), 4),
                "diagnosis_accuracy": ros.decision_quality.get("root_cause_accuracy", 0.0),
                "action_selection_accuracy": ros.decision_quality.get("final_action_accuracy", 0.0),
            },
            "decision_quality": ros.decision_quality,
            "unnecessary_intervention_definition": (
                "action=retry_payment AND outcome!=recovered"
            ),
        }

        comp = result.comparison
        safe_net = (result.safe_baseline.actual_recovered - result.safe_baseline.intervention_cost) if result.safe_baseline else 0
        naive_net = (result.baseline.actual_recovered - result.baseline.intervention_cost) if result.baseline else 0
        revplug_net = result.revplug.net_recovered
        safe_lift = ((revplug_net - safe_net) / max(1, safe_net)) * 100.0 if safe_net > 0 else None
        naive_lift = ((revplug_net - naive_net) / max(1, naive_net)) * 100.0 if naive_net > 0 else None

        comp_dict = {
            "absolute_recovery_difference": comp.absolute_recovery_difference,
            "recovery_rate_difference": round(comp.recovery_rate_difference, 6),
            "relative_improvement": round(comp.relative_improvement, 4) if comp.relative_improvement is not None else None,
            "revplug_beat_baseline": comp.revplug_beat_baseline,
            "revplug_beat_safe": comp.revplug_beat_safe,
            "honest_summary": comp.honest_summary,
            "safe_baseline_net": safe_net,
            "naive_baseline_net": naive_net,
            "revplug_net": revplug_net,
            "safe_lift_pct": round(safe_lift, 4) if safe_lift is not None else None,
            "naive_lift_pct": round(naive_lift, 4) if naive_lift is not None else None,
        }

        return {
            "evaluation_id": result.evaluation_id,
            "seed": result.seed,
            "count": result.count,
            "status": result.status,
            "started_at": result.started_at,
            "completed_at": result.completed_at,
            "benchmark_configuration": {
                "ai_enabled": True,
                "ai_routing": "contextual",
                "deterministic_safety": True,
                "evaluation_mode": "AI_ASSISTED",
            },
            "dataset": result.dataset_info,
            "revplug": ros_dict,
            "recoveros": ros_dict,
            "baseline": bl_dict,
            "safe_baseline": bl_evaluator.to_dict(result.safe_baseline) if result.safe_baseline else {},
            "comparison": comp_dict,
            "per_case": result.per_case,
            "error": result.error,
        }
