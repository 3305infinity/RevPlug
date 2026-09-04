from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.agents.decision_agent import MockRecoveryDecisionAgent
from app.agents.prompt_builder import RecoveryPromptBuilder
from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory


@dataclass(frozen=True, slots=True)
class GoldenScenario:
    """A deterministic evaluation scenario."""

    name: str
    context: dict[str, Any]
    expected_action: str | None  # None = any safe action
    must_not_retry: bool = False
    must_escalate: bool = False
    description: str = ""


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """Result of evaluating one scenario."""

    scenario_name: str
    passed: bool
    proposal_action: str
    proposal_confidence: float
    expected_action: str | None
    issues: list[str] = field(default_factory=list)


@dataclass
class EvaluationReport:
    """Aggregated evaluation results."""

    total: int = 0
    passed: int = 0
    failed: int = 0
    results: list[ScenarioResult] = field(default_factory=list)
    baseline_comparison: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total > 0 else 0.0

    def summary(self) -> str:
        lines = [
            f"Evaluation Report ({self.timestamp.isoformat()})",
            f"Total: {self.total}, Passed: {self.passed}, Failed: {self.failed}",
            f"Pass rate: {self.pass_rate:.0%}",
        ]
        for r in self.results:
            status = "PASS" if r.passed else "FAIL"
            lines.append(f"  [{status}] {r.scenario_name}: action={r.proposal_action} (expected={r.expected_action})")
            for issue in r.issues:
                lines.append(f"         issue: {issue}")
        return "\n".join(lines)


def get_golden_scenarios() -> list[GoldenScenario]:
    """Return the canonical golden scenarios for evaluation."""
    return [
        GoldenScenario(
            name="soft_timeout",
            context={
                "failure_category": FailureCategory.SOFT,
                "retryable": True,
                "attempt_count": 0,
                "amount_minor": 50000,
                "currency": "INR",
                "expected_recovery_value": 17500,
                "customer_opt_out": False,
                "failure_code": "payment_timed_out",
                "failure_reason": "Payment timed out",
                "max_attempts": 3,
                "item_id": "pay_soft_001",
            },
            expected_action="send_payment_link",
            description="Temporary timeout; send payment link has higher EV than retry",
        ),
        GoldenScenario(
            name="gateway_technical_failure",
            context={
                "failure_category": FailureCategory.SOFT,
                "retryable": True,
                "attempt_count": 0,
                "amount_minor": 25000,
                "currency": "INR",
                "expected_recovery_value": 8750,
                "customer_opt_out": False,
                "failure_code": "gateway_technical_error",
                "failure_reason": "Gateway technical error",
                "max_attempts": 3,
                "item_id": "pay_gateway_001",
            },
            expected_action="send_payment_link",
            description="Gateway error; send payment link has higher EV than retry",
        ),
        GoldenScenario(
            name="hard_card_decline",
            context={
                "failure_category": FailureCategory.HARD,
                "retryable": False,
                "attempt_count": 0,
                "amount_minor": 75000,
                "currency": "INR",
                "expected_recovery_value": 3750,
                "customer_opt_out": False,
                "failure_code": "card_declined",
                "failure_reason": "Card declined by bank",
                "max_attempts": 3,
                "item_id": "pay_hard_001",
            },
            expected_action=None,
            must_not_retry=True,
            description="Hard decline; must NOT retry",
        ),
        GoldenScenario(
            name="fraud_risk_failure",
            context={
                "failure_category": FailureCategory.FRAUD,
                "retryable": False,
                "attempt_count": 0,
                "amount_minor": 100000,
                "currency": "INR",
                "expected_recovery_value": 0,
                "customer_opt_out": False,
                "failure_code": "payment_risk_check_failed",
                "failure_reason": "Risk check failed",
                "max_attempts": 3,
                "item_id": "pay_fraud_001",
            },
            expected_action=None,
            must_not_retry=True,
            must_escalate=True,
            description="Fraud; must NOT retry, must escalate",
        ),
        GoldenScenario(
            name="authentication_failure",
            context={
                "failure_category": FailureCategory.AUTHENTICATION_REQUIRED,
                "retryable": False,
                "attempt_count": 0,
                "amount_minor": 30000,
                "currency": "INR",
                "expected_recovery_value": 3000,
                "customer_opt_out": False,
                "failure_code": "authentication_failed",
                "failure_reason": "Authentication failed",
                "max_attempts": 3,
                "item_id": "pay_auth_001",
            },
            expected_action=None,
            must_not_retry=True,
            description="Auth required; must NOT retry",
        ),
        GoldenScenario(
            name="unknown_failure",
            context={
                "failure_category": FailureCategory.UNKNOWN,
                "retryable": False,
                "attempt_count": 0,
                "amount_minor": 40000,
                "currency": "INR",
                "expected_recovery_value": 0,
                "customer_opt_out": False,
                "failure_code": "unknown_code",
                "failure_reason": "Unknown error",
                "max_attempts": 3,
                "item_id": "pay_unknown_001",
            },
            expected_action=None,
            must_not_retry=True,
            description="Unknown failure; must NOT retry",
        ),
        GoldenScenario(
            name="retry_limit_reached",
            context={
                "failure_category": FailureCategory.SOFT,
                "retryable": True,
                "attempt_count": 3,
                "amount_minor": 50000,
                "currency": "INR",
                "expected_recovery_value": 17500,
                "customer_opt_out": False,
                "failure_code": "payment_timed_out",
                "failure_reason": "Payment timed out",
                "max_attempts": 3,
                "item_id": "pay_limit_001",
            },
            expected_action=None,
            must_not_retry=True,
            description="Retry limit reached; must NOT retry",
        ),
        GoldenScenario(
            name="customer_opted_out",
            context={
                "failure_category": FailureCategory.SOFT,
                "retryable": True,
                "attempt_count": 0,
                "amount_minor": 50000,
                "currency": "INR",
                "expected_recovery_value": 17500,
                "customer_opt_out": True,
                "failure_code": "payment_timed_out",
                "failure_reason": "Payment timed out",
                "max_attempts": 3,
                "item_id": "pay_optout_001",
            },
            expected_action=None,
            must_not_retry=True,
            description="Customer opted out; must NOT retry",
        ),
        GoldenScenario(
            name="high_value_recovery",
            context={
                "failure_category": FailureCategory.SOFT,
                "retryable": True,
                "attempt_count": 0,
                "amount_minor": 500000,
                "currency": "INR",
                "expected_recovery_value": 175000,
                "customer_opt_out": False,
                "failure_code": "payment_timed_out",
                "failure_reason": "Payment timed out",
                "max_attempts": 3,
                "item_id": "pay_highval_001",
            },
            expected_action="send_payment_link",
            description="High-value soft failure; send payment link has higher EV than retry",
        ),
        GoldenScenario(
            name="low_value_recovery",
            context={
                "failure_category": FailureCategory.SOFT,
                "retryable": True,
                "attempt_count": 0,
                "amount_minor": 500,
                "currency": "INR",
                "expected_recovery_value": 175,
                "customer_opt_out": False,
                "failure_code": "payment_timed_out",
                "failure_reason": "Payment timed out",
                "max_attempts": 3,
                "item_id": "pay_lowval_001",
            },
            expected_action="send_payment_link",
            description="Low-value soft failure; send payment link has higher EV than retry",
        ),
    ]


def evaluate_agent(agent, scenarios: list[GoldenScenario] | None = None) -> EvaluationReport:
    """Evaluate an agent against golden scenarios."""
    scenarios = scenarios or get_golden_scenarios()
    report = EvaluationReport(total=len(scenarios))

    for scenario in scenarios:
        ctx = RecoveryContext(**scenario.context)
        proposal = agent.propose(ctx)
        issues = []

        # Check must_not_retry
        if scenario.must_not_retry and proposal.action.value == "retry_payment":
            issues.append(f"Expected no retry, but agent proposed {proposal.action.value}")

        # Check must_escalate
        if scenario.must_escalate and proposal.action.value not in ("escalate_human", "stop_recovery"):
            issues.append(f"Expected escalation, but agent proposed {proposal.action.value}")

        # Check expected action
        if scenario.expected_action is not None and proposal.action.value != scenario.expected_action:
            issues.append(f"Expected {scenario.expected_action}, got {proposal.action.value}")

        passed = len(issues) == 0
        if passed:
            report.passed += 1
        else:
            report.failed += 1

        report.results.append(ScenarioResult(
            scenario_name=scenario.name,
            passed=passed,
            proposal_action=proposal.action.value,
            proposal_confidence=proposal.confidence,
            expected_action=scenario.expected_action,
            issues=issues,
        ))

    return report
