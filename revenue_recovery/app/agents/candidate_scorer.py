"""Candidate generation and EV-based ranking for recovery proposals."""
from __future__ import annotations

from typing import Any

from app.domain.actions import ActionRegistry
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.proposals import CandidateScore, RecoveryAction, RecoveryProposal
from app.scoring.expected_value import ExpectedValueScorer
from app.scoring.memory import RecoveryMemoryStore


def _eligible_candidates(context: RecoveryContext) -> list[str]:
    """Return 3-6 eligible action strings from the ActionRegistry for the given context."""
    all_actions = [a.value for a in RecoveryAction if a not in {RecoveryAction.WAIT, RecoveryAction.NO_ACTION}]
    eligible: list[str] = []

    category = context.failure_category
    is_fraud = category == FailureCategory.FRAUD
    is_auth = category == FailureCategory.AUTHENTICATION_REQUIRED
    is_hard = category == FailureCategory.HARD
    is_soft = category == FailureCategory.SOFT
    is_unknown = category == FailureCategory.UNKNOWN
    prev = set(context.previous_actions)
    last_obs = context.last_observation or {}
    last_status = last_obs.get("status")
    last_action = last_obs.get("action")

    if is_fraud or context.customer_opt_out:
        return [RecoveryAction.STOP_RECOVERY.value]

    if is_auth:
        eligible = [
            RecoveryAction.SEND_PAYMENT_LINK.value,
            RecoveryAction.SEND_CUSTOMER_MESSAGE.value,
            RecoveryAction.ALTERNATE_CHANNEL.value,
            RecoveryAction.ESCALATE_HUMAN.value,
            RecoveryAction.WAIT.value,
        ]
    elif is_soft:
        if last_action == "retry_payment" and last_status == "failed":
            eligible = [
                RecoveryAction.SEND_PAYMENT_LINK.value,
                RecoveryAction.ALTERNATE_CHANNEL.value,
                RecoveryAction.SEND_REMINDER.value,
                RecoveryAction.ESCALATE_HUMAN.value,
            ]
        else:
            eligible = [
                RecoveryAction.RETRY_PAYMENT.value,
                RecoveryAction.SEND_PAYMENT_LINK.value,
                RecoveryAction.SEND_REMINDER.value,
                RecoveryAction.ALTERNATE_CHANNEL.value,
                RecoveryAction.SEND_CUSTOMER_MESSAGE.value,
                RecoveryAction.WAIT.value,
            ]
        if context.attempt_count >= context.max_attempts:
            eligible = [a for a in eligible if a != RecoveryAction.RETRY_PAYMENT.value]
    elif is_hard:
        eligible = [
            RecoveryAction.SEND_PAYMENT_LINK.value,
            RecoveryAction.ALTERNATE_CHANNEL.value,
            RecoveryAction.SEND_REMINDER.value,
            RecoveryAction.ESCALATE_HUMAN.value,
        ]
        if context.attempt_count >= 2:
            eligible = [RecoveryAction.ESCALATE_HUMAN.value]
    else:
        eligible = [
            RecoveryAction.SEND_PAYMENT_LINK.value,
            RecoveryAction.SEND_CUSTOMER_MESSAGE.value,
            RecoveryAction.ALTERNATE_CHANNEL.value,
            RecoveryAction.ESCALATE_HUMAN.value,
        ]

    if is_unknown:
        eligible = [RecoveryAction.ESCALATE_HUMAN.value]

    # Deduplicate while preserving order
    seen: set[str] = set()
    result: list[str] = []
    for a in eligible:
        if a not in seen and ActionRegistry.is_valid(a):
            seen.add(a)
            result.append(a)
    return result[:6]


def _score_candidates(
    context: RecoveryContext,
    eligible_actions: list[str],
    scorer: ExpectedValueScorer | None = None,
) -> list[CandidateScore]:
    """Score each eligible action using the existing EV formula."""
    scorer = scorer or ExpectedValueScorer()
    attempt_number = max(1, context.attempt_count)
    scored: list[CandidateScore] = []
    for action in eligible_actions:
        result = scorer.score(
            amount_minor=context.amount_minor,
            failure_category=context.failure_category.value
            if hasattr(context.failure_category, "value")
            else str(context.failure_category),
            proposed_action=action,
            attempt_number=attempt_number,
            context={
                "retryable": context.retryable,
                "customer_opt_out": context.customer_opt_out,
                "attempt_count": context.attempt_count,
                **(context.metadata or {}),
            },
        )
        scored.append(
            CandidateScore(
                action=RecoveryAction(action),
                recovery_probability=result.recovery_probability,
                intervention_cost=result.intervention_cost,
                gross_expected_recovery=result.metadata.get("gross_expected_recovery", result.expected_recovery_value + result.intervention_cost),
                net_expected_recovery=result.expected_recovery_value,
                reason=result.scoring_reason,
            )
        )
    scored.sort(key=lambda c: c.net_expected_recovery, reverse=True)
    return scored


def _data_driven_confidence(
    context: RecoveryContext,
    scored: list[CandidateScore],
    memory_store: RecoveryMemoryStore | None = None,
) -> float:
    """Compute confidence from comparable historical outcomes, not hardcoded literals."""
    memory = memory_store.get_memory(context.customer_id) if memory_store is not None else None
    top = scored[0] if scored else None
    if top is None:
        return 0.5

    action_key = top.action.value if isinstance(top.action, RecoveryAction) else str(top.action)
    comparable = 0
    if memory is not None:
        stats = memory.channel_stats.get(action_key)
        if stats is not None:
            comparable = stats.total_attempts

    if comparable >= 20:
        base = 0.90
    elif comparable >= 10:
        base = 0.80
    elif comparable >= 5:
        base = 0.70
    elif comparable >= 2:
        base = 0.60
    elif comparable >= 1:
        base = 0.55
    else:
        base = 0.50

    is_stop_action = action_key == RecoveryAction.STOP_RECOVERY.value
    if is_stop_action:
        return min(base + 0.05, 0.95)

    amount = max(context.amount_minor, 1)
    gross_ratio = (top.gross_expected_recovery or 0) / amount
    net_ratio = top.net_expected_recovery / amount
    if gross_ratio >= 0.5:
        base = min(base + 0.05, 0.95)
    elif net_ratio <= 0:
        base = max(base - 0.05, 0.30)

    return max(0.0, min(0.95, base))


def build_ranked_proposal(
    context: RecoveryContext,
    *,
    scorer: ExpectedValueScorer | None = None,
    memory_store: RecoveryMemoryStore | None = None,
    model_name: str = "mock",
) -> RecoveryProposal:
    """Build a recovery proposal with ranked candidates and data-driven confidence."""
    eligible = _eligible_candidates(context)
    scored = _score_candidates(context, eligible, scorer=scorer)
    confidence = _data_driven_confidence(context, scored, memory_store=memory_store)

    top = scored[0] if scored else None
    if top is None:
        return RecoveryProposal(
            action=RecoveryAction.NO_ACTION,
            reason="No eligible actions",
            confidence=0.5,
            model_name=model_name,
            candidates=[],
        )

    primary_reason = top.reason or f"{top.action.value} selected with highest EV ({_fmt_ev(top.net_expected_recovery)})"
    return RecoveryProposal(
        action=top.action,
        reason=primary_reason,
        confidence=confidence,
        model_name=model_name,
        evidence={
            "candidate_count": len(scored),
            "top_net_ev": top.net_expected_recovery,
            "top_probability": top.recovery_probability,
        },
        diagnosis={"diagnosis_source": "rules", "ranking_method": "ev_net"},
        candidates=scored,
    )


def _fmt_ev(value: int) -> str:
    try:
        return f"₹{value / 100:.2f}"
    except Exception:
        return str(value)
