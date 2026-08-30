"""Baseline Evaluator — dumb fixed-strategy comparator.

THIS IS NOT A RECOVERY ENGINE. It is a comparator that applies a fixed
strategy to the same evaluation dataset that RecoverOS processes. The
baseline allows a judge to compare the value of RecoverOS's intelligent
decisions versus a naive approach.

Baseline strategy (fixed, unchanged):
    Attempt 1: retry_payment
    If failed and attempt_budget > 0: attempt 2: retry_payment
    If still failed: stop

The baseline:
- Does NOT use AI diagnosis
- Does NOT use Expected Recovery optimization
- Does NOT use customer history optimization
- Does NOT choose between intelligent interventions
- Does NOT use confidence thresholds
- Does NOT enforce policy (opt-out, fraud, retry budget)
- DOES use the exact same simulated payment outcome model as RecoverOS
- DOES use the exact same recovery probability model to simulate success/failure

IMPORTANT: The baseline deliberately ignores opt-out and fraud signals.
This is intentional — it shows the risk of a dumb strategy.
RecoverOS's avoidance of these cases is a genuine safety/compliance advantage.

Definition of Unnecessary Intervention (used by BOTH systems):
    An intervention is unnecessary when:
        action was "retry_payment"
        AND outcome was NOT "recovered"
    i.e. intervention cost was spent but no money was recovered.

This definition is based on observable canonical action + outcome data.
It cannot be gamed because it does not depend on which system made the decision.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.models import RecoveryItem
from app.scoring.probability import RecoveryProbabilityModel


# ---------------------------------------------------------------------------
# Result Types
# ---------------------------------------------------------------------------

@dataclass
class BaselineCaseResult:
    """Result of the baseline evaluator for one case."""

    case_id: str
    amount_at_risk: int
    failure_category: str
    attempts_made: int
    outcome: str  # "recovered" | "stopped" | "processing_error"
    actual_recovered: int  # 0 unless outcome == "recovered"
    intervention_cost: int  # cost_per_attempt * attempts_made
    unnecessary_intervention: bool
    # Definition: action was retry_payment AND outcome != "recovered"
    stop_reason: str | None = None
    actions_taken: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BaselineBatchResult:
    """Aggregated result of the baseline evaluator across all cases."""

    cases_evaluated: int = 0
    cases_completed: int = 0
    cases_failed_processing: int = 0  # processing errors, not outcome failures
    total_amount_at_risk: int = 0
    actual_recovered: int = 0
    recovery_rate: float = 0.0
    recovered_count: int = 0
    stopped_count: int = 0
    total_interventions: int = 0
    intervention_cost: int = 0
    cost_per_recovery: float = 0.0
    unnecessary_interventions: int = 0
    # Raw counts reported alongside derived metric for transparency
    raw_retry_attempts: int = 0
    raw_retries_that_failed: int = 0
    baseline_policy_violations: dict[str, int] = field(default_factory=lambda: {
        "hard_decline_retry": 0,
        "fraud_retry": 0,
        "do_not_contact_violation": 0,
        "retry_budget_violation": 0,
        "promise_contact_violation": 0,
        "total_policy_violations": 0,
    })
    per_case: list[BaselineCaseResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Baseline Evaluator
# ---------------------------------------------------------------------------

_COST_PER_INTERVENTION = 500  # minor units — matches InterventionCostModel retry_payment cost
_MAX_RETRIES = 2               # baseline is fixed at 2 attempts, always


class BaselineEvaluator:
    """Dumb fixed-strategy comparator.

    Applies retry -> retry -> stop to every case, regardless of:
    - fraud signals
    - opt-out status
    - retry budget
    - failure category appropriateness

    Uses the same RecoveryProbabilityModel as RecoverOS to determine whether
    a retry attempt succeeds. This ensures the comparison is fair -- both
    systems face the same underlying payment success probabilities.

    The baseline is a comparator only. It must never be used in production.
    """

    def __init__(
        self,
        probability_model: RecoveryProbabilityModel | None = None,
        cost_per_intervention: int = _COST_PER_INTERVENTION,
        max_retries: int = _MAX_RETRIES,
        rng_seed: int = 0,
    ) -> None:
        self._probability_model = probability_model or RecoveryProbabilityModel()
        self._cost_per_intervention = cost_per_intervention
        self._max_retries = max_retries
        self._rng_seed = rng_seed

    def evaluate_case(self, item: RecoveryItem, case_index: int) -> BaselineCaseResult:
        """Apply fixed retry strategy to one case.

        Args:
            item: The recovery item to evaluate.
            case_index: Stable index within the batch (used for RNG salt).

        Returns:
            BaselineCaseResult with observable outcome data.
        """
        import random as _random
        rng = _random.Random(self._rng_seed + case_index * 31337)

        failure_category = item.root_cause or "unknown"
        attempts_made = 0
        actions_taken: list[str] = []
        total_cost = 0
        recovered = False

        gt = item.metadata.get("ground_truth")

        for attempt_num in range(1, self._max_retries + 1):
            actions_taken.append("retry_payment")
            attempts_made += 1
            total_cost += self._cost_per_intervention

            if gt and "action_outcomes" in gt:
                from app.datasets.synthetic import lookup_counterfactual_outcome
                succ, rec_amt, _ = lookup_counterfactual_outcome(gt, "retry_payment", attempt_num)
                if succ:
                    recovered = True
                    break
            else:
                prob = self._probability_model.estimate(
                    failure_category=failure_category,
                    proposed_action="retry_payment",
                    attempt_number=attempt_num,
                )
                if rng.random() < prob:
                    recovered = True
                    break

        outcome = "recovered" if recovered else "stopped"
        actual_recovered = item.amount_minor if recovered else 0
        stop_reason = "max_retries" if not recovered else None

        # Unnecessary intervention: action=retry AND outcome != recovered
        unnecessary = attempts_made > 0 and not recovered

        return BaselineCaseResult(
            case_id=item.id,
            amount_at_risk=item.amount_minor,
            failure_category=failure_category,
            attempts_made=attempts_made,
            outcome=outcome,
            actual_recovered=actual_recovered,
            intervention_cost=total_cost,
            unnecessary_intervention=unnecessary,
            stop_reason=stop_reason,
            actions_taken=actions_taken,
            metadata={
                "is_synthetic": item.metadata.get("is_synthetic", True),
                "original_category": item.metadata.get("original_category", failure_category),
                "customer_id": item.customer_id,
                "case_index": case_index,
            },
        )

    def evaluate_batch(self, items: list[RecoveryItem]) -> BaselineBatchResult:
        """Evaluate all items with the fixed baseline strategy.

        Args:
            items: List of RecoveryItems (same dataset as RecoverOS uses).

        Returns:
            BaselineBatchResult with aggregated metrics.
        """
        result = BaselineBatchResult()
        result.cases_evaluated = len(items)

        for idx, item in enumerate(items):
            try:
                case_result = self.evaluate_case(item, case_index=idx)
                result.per_case.append(case_result)
                result.cases_completed += 1
                result.total_amount_at_risk += item.amount_minor
                result.actual_recovered += case_result.actual_recovered
                result.total_interventions += case_result.attempts_made
                result.intervention_cost += case_result.intervention_cost
                result.raw_retry_attempts += case_result.attempts_made
                result.raw_retries_that_failed += (
                    case_result.attempts_made if not case_result.actual_recovered else
                    max(0, case_result.attempts_made - 1)
                )
                if case_result.outcome == "recovered":
                    result.recovered_count += 1
                else:
                    result.stopped_count += 1
                if case_result.unnecessary_intervention:
                    result.unnecessary_interventions += 1

                # Track baseline safety/policy violations across 10 categories
                cat = (item.root_cause or "").lower()
                orig_cat = str(item.metadata.get("original_category", "")).lower()
                is_optout = bool(item.metadata.get("customer_opted_out"))
                att_count = int(item.metadata.get("attempt_count", 0))
                is_promise = item.metadata.get("promise_status") == "promised"
                is_expired = item.metadata.get("promise_status") == "expired" or orig_cat == "soft_promise_expired"
                is_disputed = bool(item.metadata.get("disputed"))
                is_cancelled = bool(item.metadata.get("cancelled"))
                status_str = item.status.value if hasattr(item.status, "value") else str(item.status)
                is_terminal = status_str in ("recovered", "stopped", "escalated")

                if cat in ("fraud", "security_or_fraud") or orig_cat == "fraud" or item.metadata.get("fraud_flag"):
                    result.baseline_policy_violations["fraud_retry"] += 1
                    result.baseline_policy_violations["total_policy_violations"] += 1
                if is_optout:
                    result.baseline_policy_violations["do_not_contact_violation"] += 1
                    result.baseline_policy_violations["total_policy_violations"] += 1
                if cat in ("hard", "hard_decline") or orig_cat == "hard":
                    result.baseline_policy_violations["hard_decline_retry"] += 1
                    result.baseline_policy_violations["total_policy_violations"] += 1
                if att_count >= 3 or orig_cat == "soft_exhausted":
                    result.baseline_policy_violations["retry_budget_violation"] += 1
                    result.baseline_policy_violations["total_policy_violations"] += 1
                if is_promise or orig_cat == "soft_promise_active":
                    result.baseline_policy_violations["promise_contact_violation"] += 1
                    result.baseline_policy_violations["total_policy_violations"] += 1
                if is_expired:
                    result.baseline_policy_violations.setdefault("expired_case_violations", 0)
                    result.baseline_policy_violations["expired_case_violations"] += 1
                    result.baseline_policy_violations["total_policy_violations"] += 1
                if is_disputed:
                    result.baseline_policy_violations.setdefault("disputed_invoice_violations", 0)
                    result.baseline_policy_violations["disputed_invoice_violations"] += 1
                    result.baseline_policy_violations["total_policy_violations"] += 1
                if is_cancelled:
                    result.baseline_policy_violations.setdefault("cancelled_subscription_violations", 0)
                    result.baseline_policy_violations["cancelled_subscription_violations"] += 1
                    result.baseline_policy_violations["total_policy_violations"] += 1
                if is_terminal:
                    result.baseline_policy_violations.setdefault("terminal_state_violations", 0)
                    result.baseline_policy_violations["terminal_state_violations"] += 1
                    result.baseline_policy_violations["total_policy_violations"] += 1

            except Exception as exc:
                result.cases_failed_processing += 1
                result.per_case.append(BaselineCaseResult(
                    case_id=item.id,
                    amount_at_risk=item.amount_minor,
                    failure_category=item.root_cause or "unknown",
                    attempts_made=0,
                    outcome="processing_error",
                    actual_recovered=0,
                    intervention_cost=0,
                    unnecessary_intervention=False,
                    stop_reason=f"processing_error: {exc}",
                    metadata={"error": str(exc)},
                ))

        # Compute rates safely
        if result.total_amount_at_risk > 0:
            result.recovery_rate = result.actual_recovered / result.total_amount_at_risk
        if result.recovered_count > 0:
            result.cost_per_recovery = result.intervention_cost / result.recovered_count

        return result

    def to_dict(self, batch_result: BaselineBatchResult) -> dict[str, Any]:
        """Serialize a batch result to a JSON-safe dict."""
        return {
            "cases_evaluated": batch_result.cases_evaluated,
            "cases_completed": batch_result.cases_completed,
            "cases_failed_processing": batch_result.cases_failed_processing,
            "total_amount_at_risk": batch_result.total_amount_at_risk,
            "expected_recovery": None,  # Baseline has no expected-value model
            "actual_recovered": batch_result.actual_recovered,
            "recovery_rate": round(batch_result.recovery_rate, 6),
            "recovered_count": batch_result.recovered_count,
            "stopped_count": batch_result.stopped_count,
            "escalated_count": 0,  # Baseline never escalates
            "total_interventions": batch_result.total_interventions,
            "intervention_cost": batch_result.intervention_cost,
            "cost_per_recovery": round(batch_result.cost_per_recovery, 2),
            "unnecessary_interventions": batch_result.unnecessary_interventions,
            "raw_retry_attempts": batch_result.raw_retry_attempts,
            "raw_retries_that_failed": batch_result.raw_retries_that_failed,
            "baseline_policy_violations": batch_result.baseline_policy_violations,
            "unnecessary_intervention_definition": (
                "action=retry_payment AND outcome!=recovered"
            ),
        }
