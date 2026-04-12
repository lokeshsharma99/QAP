"""
Judge Verdict Contract
======================

Pydantic models for the Judge Agent's output.
The JudgeVerdict represents the adversarial review of a generated specification,
including confidence score, checklist results, and approval status.
"""

from enum import Enum

from pydantic import BaseModel, Field


class ChecklistResult(BaseModel):
    """Result of a single checklist item."""

    check_item: str = Field(description="Name of the checklist item")
    passed: bool = Field(description="Whether this check passed")
    notes: str = Field(default="", description="Additional notes or reasons for failure")


class RejectionReason(str, Enum):
    """Reasons for rejecting a specification."""

    SYNTAX_ERROR = "syntax_error"
    UNCLEAR_REQUIREMENTS = "unclear_requirements"
    MISSING_TRACEABILITY = "missing_traceability"
    NON_REUSABLE_STEPS = "non_reusable_steps"
    INSUFFICIENT_COVERAGE = "insufficient_coverage"
    DATA_REQUIREMENTS_MISSING = "data_requirements_missing"
    OTHER = "other"


class JudgeVerdict(BaseModel):
    """Adversarial review of a generated specification.

    Produced by the Judge Agent after running the DoD checklist.
    Used to determine if a spec is ready for implementation.
    """

    confidence: float = Field(
        ge=0.0,
        le=100.0,
        description="Confidence score (0-100). Auto-approve at ≥90."
    )
    passed: bool = Field(description="Whether the specification passed the review")
    checklist_results: list[ChecklistResult] = Field(
        default_factory=list,
        description="Results of each checklist item"
    )
    rejection_reasons: list[RejectionReason] = Field(
        default_factory=list,
        description="Reasons for rejection if failed"
    )
    requires_human: bool = Field(
        default=False,
        description="Whether human review is required regardless of confidence"
    )
    timestamp: str = Field(description="ISO 8601 timestamp of the review")
    reviewed_item_type: str = Field(
        default="",
        description="Type of item reviewed (e.g., 'GherkinSpec', 'RequirementContext')"
    )
    reviewed_item_id: str = Field(
        default="",
        description="Identifier of the reviewed item (e.g., ticket_id, spec_id)"
    )
    feedback: str = Field(
        default="",
        description="Detailed feedback for improvement if rejected"
    )
