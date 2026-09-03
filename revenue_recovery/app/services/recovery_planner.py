"""Recovery Planner for generating and versioning multi-step recovery plans.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.plan import RecoveryPlan
from app.domain.proposals import RecoveryAction


class RecoveryPlanner:
    """Generates bounded multi-step recovery plans based on context and AI candidate rankings."""

    def __init__(
        self,
        *,
        default_max_retries: int = 3,
        default_max_contacts: int = 2,
        default_max_cost_minor: int = 2000,
        default_ttl_seconds: int = 86400,
    ) -> None:
        self._max_retries = default_max_retries
        self._max_contacts = default_max_contacts
        self._max_cost_minor = default_max_cost_minor
        self._ttl_seconds = default_ttl_seconds

    def create_plan(
        self,
        context: RecoveryContext,
        ai_recommendation: Any | None = None,
        candidate_actions: list[str] | None = None,
    ) -> RecoveryPlan:
        """Create a new versioned RecoveryPlan for a case."""
        case_id = context.item_id
        plan_id = f"plan_{uuid.uuid4().hex[:12]}"
        category = context.failure_category

        # Hard stop conditions
        stop_conds = [
            "payment_recovered",
            "customer_opted_out",
            "fraud_detected",
            "hard_decline",
            "retry_budget_exhausted",
            "contact_budget_exhausted",
            "workflow_ttl_expired",
            "negative_expected_value",
            "terminal_state_reached",
        ]

        # Determine ordered actions
        ordered: list[str] = []

        if category == FailureCategory.FRAUD or context.customer_opt_out:
            ordered = ["stop_recovery"]
        elif category == FailureCategory.HARD:
            ordered = ["send_payment_link", "stop_recovery"]
        elif category == FailureCategory.SOFT:
            if context.attempt_count < self._max_retries and context.retryable:
                ordered = ["retry_payment", "send_payment_link", "stop_recovery"]
            else:
                ordered = ["send_payment_link", "stop_recovery"]
        elif category == FailureCategory.AUTHENTICATION_REQUIRED:
            ordered = ["send_customer_message", "send_payment_link", "stop_recovery"]
        else:
            # Check candidate actions or AI recommendation
            if candidate_actions:
                ordered = [a for a in candidate_actions if a != "retry_payment" or (context.attempt_count < self._max_retries and context.retryable)]
            else:
                ordered = ["escalate_human"]

        if not ordered:
            ordered = ["stop_recovery"]

        # Override with AI recommendation if provided and valid
        if ai_recommendation and hasattr(ai_recommendation, "selected_action"):
            sel = ai_recommendation.selected_action
            if isinstance(sel, RecoveryAction):
                sel = sel.value
            if sel in ordered and sel != ordered[0]:
                ordered.remove(sel)
                ordered.insert(0, sel)

        return RecoveryPlan(
            case_id=case_id,
            plan_id=plan_id,
            version=1,
            diagnosis=f"Diagnosed {category.value if hasattr(category, 'value') else category} failure",
            objective="maximize_net_recovery",
            ordered_actions=ordered,
            current_step_index=0,
            max_steps=min(len(ordered), 4),
            max_payment_retries=self._max_retries,
            max_contact_attempts=self._max_contacts,
            max_total_cost_minor=self._max_cost_minor,
            workflow_ttl_seconds=self._ttl_seconds,
            stop_conditions=stop_conds,
        )

    def build_plan(self, item: Any, primary_action: str = "retry_payment", max_attempts: int = 3) -> RecoveryPlan:
        """Legacy helper for building plan from item and primary action."""
        from app.domain.context import RecoveryContext
        from app.domain.failures import FailureCategory
        cat_str = getattr(item, "root_cause", "soft") or "soft"
        if cat_str == "mandate_failed":
            cat = FailureCategory.MANDATE_FAILURE
        else:
            try:
                cat = FailureCategory(cat_str)
            except ValueError:
                cat = FailureCategory.SOFT
        ctx = RecoveryContext(item_id=getattr(item, "id", "item_1"), failure_category=cat, max_attempts=max_attempts)
        return self.create_plan(ctx, candidate_actions=[primary_action, "send_payment_link", "stop_recovery"])


# Alias for backward compatibility
DefaultRecoveryPlanner = RecoveryPlanner
