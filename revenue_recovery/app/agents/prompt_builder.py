from __future__ import annotations

from app.domain.context import RecoveryContext
from app.domain.proposals import RecoveryAction


class RecoveryPromptBuilder:
    """Builds optimized prompts for free/low-performance LLMs.

    Design principles for weak models:
    - Short, explicit instructions
    - Schema-first output requirement
    - Minimal context (only relevant fields)
    - No unnecessary conversational text
    - Deterministic constraints
    """

    SYSTEM_PROMPT = """You are a revenue recovery decision agent for failed payments.

OBJECTIVE: Recommend the safest recovery action that maximizes expected recovery value.

CONSTRAINTS:
- Never execute payments or claim an action was executed.
- Never override policy or invent customer/payment facts.
- Unknown information must be treated conservatively.
- Fraud/risk signals must never be retried.
- Hard failures must not be blindly retried.
- Output ONLY the required JSON schema.

ALLOWED ACTIONS:
- retry_payment: retry the same payment method
- send_payment_link: send a payment link to the customer via email/SMS
- send_customer_message: send a customer recovery message (for re-authentication, reminders)
- send_reminder: send a gentle payment reminder (for overdue receivables)
- alternate_channel: try a different collection channel (WhatsApp, IVR, agent call)
- escalate_human: escalate to a human agent
- stop_recovery: stop all recovery attempts

OUTPUT SCHEMA (JSON only, no markdown):
{"action": "<action>", "confidence": <0.0-1.0>, "reasoning": "<1-3 sentences>", "risk_level": "<low|medium|critical>", "requires_human_approval": <true|false>}

RISK LEVELS:
- low: safe to auto-execute (e.g., soft temporary failure)
- medium: proceed with caution or human review
- critical: never auto-execute (fraud, high-value, ambiguous)

REQUIRES_HUMAN_APPROVAL:
- true: fraud, high-value (>$100), low confidence (<0.6), unknown failures
- false: clear temporary failures within policy"""

    def build_user_prompt(self, context: RecoveryContext) -> str:
        """Build compact context prompt with only relevant fields."""
        amount_dollars = context.amount_minor / 100

        lines = [
            "--- RECOVERY CONTEXT ---",
            f"Failure category: {context.failure_category.value}",
            f"Retryable: {context.retryable}",
            f"Attempt: {context.attempt_count}/{context.max_attempts}",
            f"Amount: {context.amount_minor} {context.currency} (${amount_dollars:.2f})",
            f"Expected recovery value: {context.expected_recovery_value}",
            f"Customer opted out: {context.customer_opt_out}",
        ]

        if context.previous_actions:
            lines.append(f"Previous actions: {', '.join(context.previous_actions)}")
        if context.failure_code:
            lines.append(f"Failure code: {context.failure_code}")
        if context.failure_reason:
            lines.append(f"Failure reason: {context.failure_reason}")
        if context.payment_method:
            lines.append(f"Payment method: {context.payment_method}")

        lines.append("---")
        lines.append("Output the recovery decision JSON now.")

        return "\n".join(lines)

    def build_user_prompt_from_dict(self, context: dict) -> str:
        """Build prompt from a flat dict (for evaluation scenarios)."""
        lines = ["--- RECOVERY CONTEXT ---"]
        for key, value in context.items():
            lines.append(f"{key}: {value}")
        lines.append("---")
        lines.append("Output the recovery decision JSON now.")
        return "\n".join(lines)
