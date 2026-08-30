from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from app.scoring.cost import InterventionCostModel
from app.scoring.priority import PriorityClassifier
from app.scoring.probability import RecoveryProbabilityModel


class RecoveryScorer(Protocol):
    """Assigns an expected recovery value to a recovery case."""

    def score(
        self,
        amount_minor: int,
        failure_category: str,
        proposed_action: str,
        attempt_number: int = 1,
        context: dict[str, Any] | None = None,
    ) -> ScoreResult:
        ...


@dataclass(frozen=True, slots=True)
class ScoreResult:
    """Structured result of expected-value scoring."""

    amount_at_risk: int
    recovery_probability: float
    intervention_cost: int
    expected_recovery_value: int
    priority: str
    score_version: str = "v1"
    scoring_reason: str = ""
    scored_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


class ExpectedValueScorer:
    """Deterministic expected-value scorer.

    Formula:
        expected_recovery_value = amount_at_risk × recovery_probability − intervention_cost

    The scorer is a pure deterministic function. Same inputs always produce
    the same score. The LLM never determines the score.
    """

    def __init__(
        self,
        probability_model: RecoveryProbabilityModel | None = None,
        cost_model: InterventionCostModel | None = None,
        priority_classifier: PriorityClassifier | None = None,
    ) -> None:
        self._probability_model = probability_model or RecoveryProbabilityModel()
        self._cost_model = cost_model or InterventionCostModel()
        self._priority_classifier = priority_classifier or PriorityClassifier()

    def score(
        self,
        amount_minor: int,
        failure_category: str,
        proposed_action: str,
        attempt_number: int = 1,
        context: dict[str, Any] | None = None,
    ) -> ScoreResult:
        """Calculate expected recovery value and priority.

        Args:
            amount_minor: Amount at risk in minor currency units.
            failure_category: Normalized failure category (e.g., "soft").
            proposed_action: Proposed intervention action (e.g., "retry_payment").
            attempt_number: 1-indexed attempt number.
            context: Optional additional context for scoring metadata.

        Returns:
            ScoreResult with all scoring inputs and outputs.
        """
        if amount_minor < 0:
            raise ValueError("amount_minor must be non-negative")

        recovery_probability = self._probability_model.estimate(
            failure_category=failure_category,
            proposed_action=proposed_action,
            attempt_number=attempt_number,
            context=context,
        )

        intervention_cost = self._cost_model.estimate(proposed_action)

        # expected_value = amount × probability − intervention_cost
        gross_ev = int(amount_minor * recovery_probability)
        expected_recovery_value = gross_ev - intervention_cost
        expected_recovery_value = max(0, expected_recovery_value)

        priority = self._priority_classifier.classify(expected_recovery_value)

        scoring_reason = (
            f"{failure_category} failure + {proposed_action} "
            f"→ probability {recovery_probability:.0%}, "
            f"cost {intervention_cost}, "
            f"expected value {expected_recovery_value}"
        )

        return ScoreResult(
            amount_at_risk=amount_minor,
            recovery_probability=recovery_probability,
            intervention_cost=intervention_cost,
            expected_recovery_value=expected_recovery_value,
            priority=priority,
            scoring_reason=scoring_reason,
            metadata={
                "failure_category": failure_category,
                "proposed_action": proposed_action,
                "attempt_number": attempt_number,
                "gross_expected_recovery": gross_ev,
                "net_expected_recovery": gross_ev - intervention_cost,
                "score_version": "v1",
                **(context or {}),
            },
        )

    def evaluate_candidates(
        self,
        amount_minor: int,
        failure_category: str,
        candidate_actions: list[str] | None = None,
        attempt_number: int = 1,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Evaluate and rank multiple candidate intervention actions by expected net recovery.

        Returns:
            List of candidate dictionaries sorted descending by net_expected_recovery.
        """
        actions = candidate_actions or [
            "retry_payment",
            "send_payment_link",
            "send_customer_message",
            "send_reminder",
            "alternate_channel",
            "escalate_human",
            "stop_recovery",
        ]

        scored_candidates = []
        for action in actions:
            prob = self._probability_model.estimate(
                failure_category=failure_category,
                proposed_action=action,
                attempt_number=attempt_number,
                context=context,
            )
            cost = self._cost_model.estimate(action)
            gross_ev = int(amount_minor * prob)
            net_ev = gross_ev - cost if action != "stop_recovery" else 0
            scored_candidates.append({
                "action": action,
                "recovery_probability": round(prob, 4),
                "intervention_cost": cost,
                "gross_expected_recovery": gross_ev,
                "net_expected_recovery": net_ev,
            })

        # Sort by net_expected_recovery descending
        scored_candidates.sort(key=lambda c: c["net_expected_recovery"], reverse=True)
        return scored_candidates
