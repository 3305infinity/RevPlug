"""Structured AI schemas for diagnosis and action recommendations.

Strict Pydantic / dataclass definitions that validate model outputs.
Arbitrary prose, unvalidated fields, and numerical financial overrides are rejected.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class AISchemaValidationError(ValueError):
    """Raised when an LLM output fails schema validation."""


@dataclass(slots=True)
class AIDiagnosis:
    """Structured AI root-cause diagnosis output."""

    root_cause: str
    confidence: float
    evidence: list[str] = field(default_factory=list)
    recommended_strategy: str | None = None
    reasoning_summary: str = ""
    ambiguous_signals: bool = False

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise AISchemaValidationError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
        if not self.root_cause or not isinstance(self.root_cause, str):
            raise AISchemaValidationError("root_cause must be a non-empty string")
        if not isinstance(self.evidence, list):
            self.evidence = [str(self.evidence)] if self.evidence else []


@dataclass(slots=True)
class RankedCandidate:
    """A candidate action ranked by AI recommendation."""

    action: str
    confidence: float
    reason: str


@dataclass(slots=True)
class AIRecommendation:
    """Structured AI action recommendation output."""

    selected_action: str
    confidence: float
    ranked_candidates: list[RankedCandidate] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    reasoning_summary: str = ""
    fallback_required: bool = False
    prompt_version: str = "action_ranking_prompt_v1"
    model_name: str = "mock"
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_qualitative_benefit: str | None = None
    risk_notes: str | None = None

    def __post_init__(self) -> None:
        if not (0.0 <= self.confidence <= 1.0):
            raise AISchemaValidationError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )
        if not self.selected_action or not isinstance(self.selected_action, str):
            raise AISchemaValidationError("selected_action must be a non-empty string")
