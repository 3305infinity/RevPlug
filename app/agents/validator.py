from __future__ import annotations

from typing import Any

from app.domain.context import RecoveryContext
from app.domain.failures import FailureCategory
from app.domain.proposals import RecoveryAction, RecoveryProposal


class ProposalValidationError(Exception):
    """Raised when a RecoveryProposal fails validation."""


class ProposalValidator:
    """Strict validator for RecoveryProposal.

    Rejects:
    - Unknown actions
    - Missing required fields
    - Confidence outside 0..1
    - Malformed data
    - Action/category combinations that are obviously invalid
    - Excessively long customer messages
    - Attempts to invent unsupported capabilities
    """

    MAX_REASON_LENGTH = 2000
    MAX_MESSAGE_LENGTH = 4000

    def validate(self, proposal: RecoveryProposal, context: RecoveryContext) -> None:
        """Validate a proposal against the recovery context.

        Raises ProposalValidationError if the proposal is invalid.
        """
        self._validate_action(proposal)
        self._validate_confidence(proposal)
        self._validate_reason(proposal)
        self._validate_customer_message(proposal)
        self._validate_action_category_compatibility(proposal, context)
        self._validate_retry_consistency(proposal, context)

    def _validate_action(self, proposal: RecoveryProposal) -> None:
        if not isinstance(proposal.action, RecoveryAction):
            raise ProposalValidationError(
                f"Invalid action: {proposal.action!r}. Must be a RecoveryAction enum."
            )

    def _validate_confidence(self, proposal: RecoveryProposal) -> None:
        if not 0.0 <= proposal.confidence <= 1.0:
            raise ProposalValidationError(
                f"Confidence must be between 0.0 and 1.0, got {proposal.confidence}"
            )

    def _validate_reason(self, proposal: RecoveryProposal) -> None:
        if not proposal.reason or not proposal.reason.strip():
            raise ProposalValidationError("reason is required and must not be empty")
        if len(proposal.reason) > self.MAX_REASON_LENGTH:
            raise ProposalValidationError(
                f"reason must be {self.MAX_REASON_LENGTH} characters or fewer"
            )

    def _validate_customer_message(self, proposal: RecoveryProposal) -> None:
        if proposal.customer_message is not None:
            if len(proposal.customer_message) > self.MAX_MESSAGE_LENGTH:
                raise ProposalValidationError(
                    f"customer_message must be {self.MAX_MESSAGE_LENGTH} characters or fewer"
                )

    def _validate_action_category_compatibility(
        self, proposal: RecoveryProposal, context: RecoveryContext
    ) -> None:
        """Reject obviously invalid action/category combinations."""
        if context.failure_category == FailureCategory.FRAUD:
            if proposal.action in (
                RecoveryAction.RETRY_PAYMENT,
                RecoveryAction.SEND_PAYMENT_LINK,
                RecoveryAction.SEND_CUSTOMER_MESSAGE,
            ):
                raise ProposalValidationError(
                    f"Action {proposal.action.value!r} is not permitted for fraud-related failures"
                )

    def _validate_retry_consistency(
        self, proposal: RecoveryProposal, context: RecoveryContext
    ) -> None:
        if proposal.action == RecoveryAction.RETRY_PAYMENT:
            if not proposal.proposed_retry:
                raise ProposalValidationError(
                    "RETRY_PAYMENT action must have proposed_retry=True"
                )
            if context.attempt_count >= context.max_attempts:
                raise ProposalValidationError(
                    f"Retry attempt {context.attempt_count + 1} exceeds max_attempts={context.max_attempts}"
                )
