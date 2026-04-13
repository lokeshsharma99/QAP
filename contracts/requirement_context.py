"""
Requirement Context Contract
===========================

Pydantic models for the Architect Agent's output.
The RequirementContext represents a structured analysis of a business requirement
from a Jira ticket, including acceptance criteria, affected Page Objects, and execution plan.
"""

from enum import Enum

from pydantic import BaseModel, Field


class AcceptanceCriterionStatus(str, Enum):
    """Status of an acceptance criterion."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"


class AcceptanceCriterionPriority(str, Enum):
    """Priority level of an acceptance criterion."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class AcceptanceCriterion(BaseModel):
    """A single acceptance criterion from a business requirement."""

    criterion: str = Field(description="The acceptance criterion text")
    status: AcceptanceCriterionStatus = Field(
        default=AcceptanceCriterionStatus.NOT_STARTED,
        description="Current status of this criterion"
    )
    priority: AcceptanceCriterionPriority = Field(
        default=AcceptanceCriterionPriority.MEDIUM,
        description="Priority level for this criterion"
    )


class RequirementContext(BaseModel):
    """Structured analysis of a business requirement from a Jira ticket.

    Produced by the Architect Agent after analyzing a ticket.
    Used by the Scribe Agent to generate Gherkin specifications.
    """

    ticket_id: str = Field(description="Jira ticket ID (e.g., QA-123)")
    ticket_url: str = Field(default="", description="Full URL to the Jira ticket")
    title: str = Field(description="Ticket title")
    description: str = Field(description="Ticket description")
    acceptance_criteria: list[AcceptanceCriterion] = Field(
        default_factory=list,
        description="List of acceptance criteria extracted from the ticket"
    )
    affected_page_objects: list[str] = Field(
        default_factory=list,
        description="List of Page Object files that will be affected (e.g., HomePage.ts, LoginPage.ts)"
    )
    is_new_feature: bool = Field(
        default=False,
        description="Whether this is a new feature or a modification to existing functionality"
    )
    execution_plan: str = Field(
        default="",
        description="High-level execution plan for implementing the requirement"
    )
    priority: AcceptanceCriterionPriority = Field(
        default=AcceptanceCriterionPriority.MEDIUM,
        description="Overall priority of the requirement"
    )
    estimated_complexity: str = Field(
        default="",
        description="Estimated complexity level (e.g., low, medium, high)"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of other tickets or requirements this depends on"
    )
