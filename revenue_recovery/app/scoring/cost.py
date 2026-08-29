from __future__ import annotations

from app.domain.proposals import RecoveryAction


class InterventionCostModel:
    """Deterministic intervention cost estimator.

    Costs are expressed in the same minor currency units as amounts
    (e.g., paise for INR). They represent the estimated direct cost of
    executing the intervention, not the recovered amount.
    """

    _COSTS: dict[str, int] = {
        "retry_payment": 500,
        "send_payment_link": 200,
        "send_customer_message": 150,
        "escalate_human": 1000,
        "stop_recovery": 0,
        "no_action": 0,
    }

    _DEFAULT_COST: int = 500

    def estimate(self, action: str) -> int:
        """Return the estimated cost for an intervention action.

        Args:
            action: The proposed intervention action.

        Returns:
            Cost in minor currency units (non-negative integer).
        """
        return self._COSTS.get(action, self._DEFAULT_COST)
