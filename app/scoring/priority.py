from __future__ import annotations


class PriorityClassifier:
    """Deterministic priority classifier based on expected recovery value.

    Thresholds are chosen to align with typical synthetic/demo amounts
    used in RevPlug (₹1,000 – ₹100,000 range).
    """

    _CRITICAL_THRESHOLD: int = 50_000   # >= ₹500 expected
    _HIGH_THRESHOLD: int = 20_000       # >= ₹200 expected
    _MEDIUM_THRESHOLD: int = 5_000      # >= ₹50 expected

    def classify(self, expected_recovery_value: int) -> str:
        """Return priority level for a given expected recovery value.

        Args:
            expected_recovery_value: Expected recovery in minor units (paise).

        Returns:
            One of: "CRITICAL", "HIGH", "MEDIUM", "LOW"
        """
        if expected_recovery_value >= self._CRITICAL_THRESHOLD:
            return "CRITICAL"
        if expected_recovery_value >= self._HIGH_THRESHOLD:
            return "HIGH"
        if expected_recovery_value >= self._MEDIUM_THRESHOLD:
            return "MEDIUM"
        return "LOW"
