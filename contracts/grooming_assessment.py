"""
Grooming Assessment Contract
=============================

Pydantic models for the 3 Amigos Grooming Assessment.
The GroomingAssessment represents the collaborative review of a user story
from BA (Business Analyst), SDET (Test Engineer), and Dev (Developer) perspectives.
"""

from enum import Enum

from pydantic import BaseModel, Field


class AssessmentLevel(str, Enum):
    """Assessment level for testability, feasibility, complexity."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Recommendation(str, Enum):
    """Overall recommendation for the user story."""

    APPROVE = "approve"
    REFINE = "refine"
    REJECT = "reject"


class BAAssessment(BaseModel):
    """Business Analyst assessment (Architect perspective)."""

    testability: AssessmentLevel = Field(
        description="How testable are the requirements (High/Medium/Low)"
    )
    completeness: bool = Field(description="Whether requirements are complete and clear")
    notes: str = Field(default="", description="Additional notes from BA perspective")


class SDETAssessment(BaseModel):
    """SDET assessment (Judge perspective)."""

    automation_feasibility: AssessmentLevel = Field(
        description="How feasible is automation (High/Medium/Low)"
    )
    edge_cases: list[str] = Field(
        default_factory=list,
        description="List of identified edge cases"
    )
    risk_assessment: AssessmentLevel = Field(
        description="Risk level for automation (Low/Medium/High)"
    )
    notes: str = Field(default="", description="Additional notes from SDET perspective")


class DevAssessment(BaseModel):
    """Developer assessment (Engineer perspective)."""

    implementation_complexity: AssessmentLevel = Field(
        description="Complexity of implementation (Low/Medium/High)"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of dependencies or prerequisites"
    )
    notes: str = Field(default="", description="Additional notes from Dev perspective")


class GroomingAssessment(BaseModel):
    """Collaborative 3 Amigos assessment of a user story.

    Produced by the Grooming Team after analyzing from BA, SDET, and Dev perspectives.
    Used to provide feedback on user story quality before automation.
    """

    ticket_id: str = Field(description="Jira ticket ID (e.g., QA-123)")
    requirement_context_id: str = Field(description="Link to RequirementContext")
    ba_assessment: BAAssessment = Field(description="BA (Architect) assessment")
    sdet_assessment: SDETAssessment = Field(description="SDET (Judge) assessment")
    dev_assessment: DevAssessment = Field(description="Dev (Engineer) assessment")
    overall_recommendation: Recommendation = Field(
        description="Combined recommendation (Approve/Refine/Reject)"
    )
    timestamp: str = Field(description="ISO 8601 timestamp of the assessment")
    assessors: list[str] = Field(
        default_factory=list,
        description="List of agent IDs who participated (e.g., ['architect', 'judge', 'engineer'])"
    )
