from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Protocol

from app.domain.models import RecoveryItem


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """Result of a recovery execution attempt."""

    success: bool
    action: str
    attempt_number: int
    reason: str
    retry_eligible: bool = False
    error_code: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, object] = field(default_factory=dict)


class RecoveryExecutor(Protocol):
    """Executes a policy-approved recovery action.

    The executor ONLY receives actions that have already been approved by
    the PolicyEngine. It must NEVER bypass or second-guess policy decisions.
    """

    def execute(
        self,
        item: RecoveryItem,
        action: str,
        *,
        attempt_number: int,
        scenario: str | None = None,
    ) -> ExecutionResult:
        ...


class SimulatedRecoveryExecutor:
    """Deterministic simulated executor for testing and local development.

    Does NOT call any external API, move money, or send messages.

    Scenarios:
        "success"           → execution succeeds
        "temporary_failure" → execution fails but retry is eligible
        "permanent_failure" → execution fails and no retry is possible
        None                → defaults to "success"
    """

    def execute(
        self,
        item: RecoveryItem,
        action: str,
        *,
        attempt_number: int,
        scenario: str | None = None,
    ) -> ExecutionResult:
        if scenario is None:
            gt = item.metadata.get("ground_truth")
            if gt and "action_outcomes" in gt:
                from app.datasets.synthetic import lookup_counterfactual_outcome
                succ, rec_amt, cost_amt = lookup_counterfactual_outcome(gt, action, attempt_number)
                if succ:
                    return ExecutionResult(
                        success=True,
                        action=action,
                        attempt_number=attempt_number,
                        reason=f"Ground truth execution succeeded for {item.id}",
                        retry_eligible=False,
                        metadata={"simulated": True, "scenario": "success", "ground_truth_matched": True, "actual_recovery_minor": rec_amt, "cost_minor": cost_amt},
                    )
                else:
                    retry_elig = (attempt_number < 3 and action == "retry_payment")
                    return ExecutionResult(
                        success=False,
                        action=action,
                        attempt_number=attempt_number,
                        reason=f"Ground truth execution failed for {item.id}",
                        retry_eligible=retry_elig,
                        error_code="ground_truth_failure",
                        metadata={"simulated": True, "scenario": "failed", "ground_truth_matched": True, "cost_minor": cost_amt},
                    )
            elif item.metadata.get("probabilistic_simulation"):
                import hashlib
                seed_str = f"{item.id}:{action}:{attempt_number}"
                hash_val = int(hashlib.md5(seed_str.encode("utf-8")).hexdigest(), 16)
                sample = (hash_val % 10000) / 10000.0

                prob = getattr(item, "recovery_probability", None)
                if prob is None:
                    prob = 0.60

                if sample < prob:
                    scenario = "success"
                elif attempt_number < 3:
                    scenario = "temporary_failure"
                else:
                    scenario = "permanent_failure"
            else:
                scenario = "success"

        if scenario == "success":
            return ExecutionResult(
                success=True,
                action=action,
                attempt_number=attempt_number,
                reason=f"Simulated recovery succeeded for {item.id}",
                retry_eligible=False,
                metadata={"simulated": True, "scenario": scenario, "execution_mode": "simulation"},
            )

        if scenario == "temporary_failure":
            return ExecutionResult(
                success=False,
                action=action,
                attempt_number=attempt_number,
                reason=f"Simulated temporary failure for {item.id}; retry eligible",
                retry_eligible=True,
                error_code="temporary_failure",
                metadata={"simulated": True, "scenario": scenario, "execution_mode": "simulation"},
            )

        if scenario == "permanent_failure":
            return ExecutionResult(
                success=False,
                action=action,
                attempt_number=attempt_number,
                reason=f"Simulated permanent failure for {item.id}; no retry possible",
                retry_eligible=False,
                error_code="permanent_failure",
                metadata={"simulated": True, "scenario": scenario, "execution_mode": "simulation"},
            )

        # Unknown scenario defaults to success (safe default).
        return ExecutionResult(
            success=True,
            action=action,
            attempt_number=attempt_number,
            reason=f"Simulated recovery succeeded for {item.id} (unknown scenario '{scenario}')",
            retry_eligible=False,
            metadata={"simulated": True, "scenario": scenario, "execution_mode": "simulation"},
        )


class RazorpayRecoveryExecutor:
    """Real Razorpay Test-Mode Recovery Executor.

    Creates actual Razorpay Payment Links when RECOVERY_EXECUTION_MODE='razorpay_test'
    and valid Test-Mode credentials are configured.
    Falls back gracefully to SimulatedRecoveryExecutor if unconfigured or requested.
    """

    def __init__(self, razorpay_client: Any | None = None) -> None:
        self._simulated = SimulatedRecoveryExecutor()
        if razorpay_client is not None:
            self._client = razorpay_client
        else:
            try:
                from app.adapters.razorpay.client import RazorpayClient
                self._client = RazorpayClient()
            except Exception:
                self._client = None

    def execute(
        self,
        item: RecoveryItem,
        action: str,
        *,
        attempt_number: int,
        scenario: str | None = None,
    ) -> ExecutionResult:
        mode = os.getenv("RECOVERY_EXECUTION_MODE", "simulation").lower().strip()

        # If simulation mode explicitly requested or Razorpay unconfigured -> delegate to simulation
        if mode != "razorpay_test" or not self._client or not self._client.is_configured:
            return self._simulated.execute(item, action, attempt_number=attempt_number, scenario=scenario)

        # Execute real Razorpay Test Mode Payment Link for send_payment_link
        if action in ("send_payment_link", "SEND_PAYMENT_LINK"):
            try:
                result = self._client.create_payment_link(
                    amount_minor=item.amount_minor,
                    currency=item.currency,
                    description=f"RevPlug Payment Recovery for item {item.id}",
                    reference_id=item.id,
                    notes={
                        "recovery_item_id": item.id,
                        "customer_id": item.customer_id,
                        "source_type": item.source_type.value,
                        "attempt_number": attempt_number,
                    },
                )
                return ExecutionResult(
                    success=True,
                    action=action,
                    attempt_number=attempt_number,
                    reason=f"Razorpay Payment Link created: {result['payment_link_id']}",
                    retry_eligible=False,
                    metadata={
                        "simulated": False,
                        "execution_mode": "razorpay_test",
                        "provider": "razorpay",
                        "provider_reference": result["payment_link_id"],
                        "customer_action_url": result["payment_link_url"],
                        "payment_link_id": result["payment_link_id"],
                        "payment_link_url": result["payment_link_url"],
                        "amount_minor": item.amount_minor,
                        "currency": item.currency,
                    },
                )
            except Exception as exc:
                err_str = str(exc)
                from app.adapters.razorpay.client import RazorpayNetworkTimeoutError
                if isinstance(exc, RazorpayNetworkTimeoutError) or "timeout" in err_str.lower() or "timed out" in err_str.lower():
                    return ExecutionResult(
                        success=False,
                        action=action,
                        attempt_number=attempt_number,
                        reason=f"EXECUTION_UNKNOWN: Network timeout contacting Razorpay API for {item.id}",
                        retry_eligible=True,
                        error_code="EXECUTION_UNKNOWN",
                        metadata={
                            "simulated": False,
                            "execution_mode": "razorpay_test",
                            "provider": "razorpay",
                            "reconciliation_required": True,
                        },
                    )
                return ExecutionResult(
                    success=False,
                    action=action,
                    attempt_number=attempt_number,
                    reason=f"Razorpay Payment Link creation failed: {err_str}",
                    retry_eligible=True,
                    error_code="razorpay_api_error",
                    metadata={"simulated": False, "execution_mode": "razorpay_test", "error": err_str},
                )

        # Other actions (retry, reminder, etc.) delegate safely to simulation executor in test mode
        return self._simulated.execute(item, action, attempt_number=attempt_number, scenario=scenario)


def get_executor() -> RecoveryExecutor:
    """Factory returning configured RecoveryExecutor based on RECOVERY_EXECUTION_MODE."""
    mode = os.getenv("RECOVERY_EXECUTION_MODE", "simulation").lower().strip()
    if mode == "razorpay_test":
        return RazorpayRecoveryExecutor()
    return SimulatedRecoveryExecutor()
