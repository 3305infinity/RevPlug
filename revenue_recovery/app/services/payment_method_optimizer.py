"""Payment Method Optimization Service for RevPlug.

Evaluates alternative payment methods (Card, UPI, Bank Transfer, Netbanking, Wallet),
suppresses retries for hard-failed methods (e.g. expired_card), and selects the action/method
yielding the highest expected NET recovery value.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.models import RecoveryItem
from app.domain.context import RecoveryContext


@dataclass(frozen=True, slots=True)
class PaymentMethodCandidate:
    method: str
    action: str
    label: str
    recovery_probability: float
    expected_gross_recovery_minor: int
    transaction_cost_minor: int
    friction_penalty_minor: int
    expected_net_ev_minor: int
    historical_success_rate_pct: float
    failure_compatibility: float  # 0.0 if hard failure blocks this method
    policy_status: str  # ALLOWED, BLOCKED
    selected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "action": self.action,
            "label": self.label,
            "recovery_probability": round(self.recovery_probability, 2),
            "expected_gross_recovery_minor": self.expected_gross_recovery_minor,
            "transaction_cost_minor": self.transaction_cost_minor,
            "friction_penalty_minor": self.friction_penalty_minor,
            "expected_net_ev_minor": self.expected_net_ev_minor,
            "historical_success_rate_pct": round(self.historical_success_rate_pct, 1),
            "failure_compatibility": round(self.failure_compatibility, 2),
            "policy_status": self.policy_status,
            "selected": self.selected,
        }


@dataclass(frozen=True, slots=True)
class PaymentMethodOptimizationResult:
    original_method: str
    failure_reason: str
    selected_method: str
    selected_action: str
    historical_original_recovery_pct: float
    historical_selected_recovery_pct: float
    incremental_friction_minor: int
    expected_net_improvement_minor: int
    switch_reason: str
    candidates: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "original_method": self.original_method,
            "failure_reason": self.failure_reason,
            "selected_method": self.selected_method,
            "selected_action": self.selected_action,
            "historical_original_recovery_pct": round(self.historical_original_recovery_pct, 1),
            "historical_selected_recovery_pct": round(self.historical_selected_recovery_pct, 1),
            "incremental_friction_minor": self.incremental_friction_minor,
            "expected_net_improvement_minor": self.expected_net_improvement_minor,
            "switch_reason": self.switch_reason,
            "candidates": self.candidates,
        }


class PaymentMethodOptimizer:
    """Scored evaluation across alternative payment methods for net recovery maximization."""

    BASE_PROBABILITIES = {
        "card": {"retry_payment": 0.18, "send_payment_link": 0.55},
        "upi": {"send_payment_link": 0.71, "alternate_channel": 0.68},
        "bank_transfer": {"send_payment_link": 0.44, "alternate_channel": 0.50},
        "netbanking": {"send_payment_link": 0.48, "alternate_channel": 0.52},
        "wallet": {"send_payment_link": 0.38, "alternate_channel": 0.42},
    }

    TRANSACTION_COSTS = {
        "card": 500,
        "upi": 200,
        "bank_transfer": 300,
        "netbanking": 250,
        "wallet": 300,
    }

    HISTORICAL_SUCCESS_RATES = {
        "card": 12.5,
        "upi": 71.0,
        "bank_transfer": 44.0,
        "netbanking": 48.0,
        "wallet": 38.0,
    }

    HARD_DECLINE_REASONS = {"expired_card", "invalid_card", "account_closed", "fraud_detected", "stolen_card"}

    def optimize(
        self,
        item: RecoveryItem,
        context: RecoveryContext | None = None,
    ) -> PaymentMethodOptimizationResult:
        orig_method = str(item.metadata.get("method") or "card").lower()
        root_cause = (item.root_cause or "").lower()
        fail_reason = str(item.metadata.get("error_description") or item.root_cause or "payment_failed").lower()

        is_hard_failure = any(r in fail_reason or r in root_cause for r in self.HARD_DECLINE_REASONS)

        candidates_raw = [
            ("card", "retry_payment", "Card Auto Retry"),
            ("upi", "send_payment_link", "UPI Payment Link"),
            ("bank_transfer", "send_payment_link", "Bank Transfer Link"),
            ("netbanking", "send_payment_link", "Netbanking Link"),
        ]

        scored_candidates: list[PaymentMethodCandidate] = []

        for method_name, act, label in candidates_raw:
            # Check compatibility
            if is_hard_failure and method_name == orig_method and act == "retry_payment":
                compat = 0.0
                prob = 0.03
                pol_status = "BLOCKED"
            else:
                compat = 1.0
                prob = self.BASE_PROBABILITIES.get(method_name, {}).get(act, 0.45)
                pol_status = "ALLOWED"

            hist_rate = self.HISTORICAL_SUCCESS_RATES.get(method_name, 35.0)
            if is_hard_failure and method_name == orig_method:
                hist_rate = 3.0

            gross_ev = int(item.amount_minor * prob * compat)
            tx_cost = self.TRANSACTION_COSTS.get(method_name, 500)
            friction = 2500 if method_name != orig_method else 0
            net_ev = max(0, gross_ev - tx_cost - friction)

            scored_candidates.append(
                PaymentMethodCandidate(
                    method=method_name,
                    action=act,
                    label=label,
                    recovery_probability=prob,
                    expected_gross_recovery_minor=gross_ev,
                    transaction_cost_minor=tx_cost,
                    friction_penalty_minor=friction,
                    expected_net_ev_minor=net_ev,
                    historical_success_rate_pct=hist_rate,
                    failure_compatibility=compat,
                    policy_status=pol_status,
                )
            )

        # Sort candidates descending by Net EV
        scored_candidates.sort(key=lambda c: -c.expected_net_ev_minor)

        # Pick best eligible candidate
        best_cand = scored_candidates[0]

        # Original candidate benchmark
        orig_cand = next((c for c in scored_candidates if c.method == orig_method), scored_candidates[-1])

        net_improvement = max(0, best_cand.expected_net_ev_minor - orig_cand.expected_net_ev_minor)
        incremental_friction = best_cand.friction_penalty_minor - orig_cand.friction_penalty_minor

        if is_hard_failure:
            switch_reason = f"Hard decline on {orig_method.upper()} ({fail_reason}) — retries suppressed. Switched to {best_cand.label} (+₹{net_improvement/100:,.0f} expected net recovery)"
        else:
            switch_reason = f"Optimal Net EV selection — {best_cand.label} ({best_cand.historical_success_rate_pct}% success rate) yields higher net recovery than {orig_method.upper()}"

        final_candidates = []
        for c in scored_candidates:
            is_sel = (c.method == best_cand.method and c.action == best_cand.action)
            final_candidates.append(
                PaymentMethodCandidate(
                    method=c.method,
                    action=c.action,
                    label=c.label,
                    recovery_probability=c.recovery_probability,
                    expected_gross_recovery_minor=c.expected_gross_recovery_minor,
                    transaction_cost_minor=c.transaction_cost_minor,
                    friction_penalty_minor=c.friction_penalty_minor,
                    expected_net_ev_minor=c.expected_net_ev_minor,
                    historical_success_rate_pct=c.historical_success_rate_pct,
                    failure_compatibility=c.failure_compatibility,
                    policy_status=c.policy_status,
                    selected=is_sel,
                ).to_dict()
            )

        return PaymentMethodOptimizationResult(
            original_method=orig_method,
            failure_reason=fail_reason,
            selected_method=best_cand.method,
            selected_action=best_cand.action,
            historical_original_recovery_pct=orig_cand.historical_success_rate_pct,
            historical_selected_recovery_pct=best_cand.historical_success_rate_pct,
            incremental_friction_minor=incremental_friction,
            expected_net_improvement_minor=net_improvement,
            switch_reason=switch_reason,
            candidates=final_candidates,
        )
