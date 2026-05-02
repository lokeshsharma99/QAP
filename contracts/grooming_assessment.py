"""
Grooming Assessment Contract
=============================

Pydantic models for the INVEST User Story Scoring Assessment.
The GroomingAssessment scores a user story against 10 GDS-aligned criteria,
provides RAG status per criterion, rewrites the story to score 10/10, and
posts the assessment as a Jira comment for BA review.
"""

from enum import Enum

from pydantic import BaseModel, Field


class RAGStatus(str, Enum):
    """RAG status for each INVEST criterion."""
    RED    = "red"    # Not met
    AMBER  = "amber"  # Partially met
    GREEN  = "green"  # Fully met


class Recommendation(str, Enum):
    """Overall recommendation for the user story."""
    APPROVE = "approve"   # Score ≥ 80/100 — ready for sprint
    REFINE  = "refine"    # Score 50–79 — BA should update story
    REJECT  = "reject"    # Score < 50 — story needs significant rework


class CriterionScore(BaseModel):
    """Score and RAG status for a single INVEST criterion."""
    criterion: str = Field(description="Criterion name (e.g. 'Independent')")
    score: int = Field(ge=1, le=10, description="Score 1-10")
    rag: RAGStatus = Field(description="Red/Amber/Green status")
    finding: str = Field(description="What was found — specific issue or confirmation")
    recommendation: str = Field(description="Specific improvement recommendation")


class GroomingAssessment(BaseModel):
    """INVEST scoring assessment of a user story.

    Produced by the Grooming Workflow after analysing the story against 10 criteria.
    The enhanced story and full scorecard are posted as a Jira comment for BA review.
    """

    ticket_id: str = Field(description="Jira ticket ID (e.g., GDS-5)")
    original_story: str = Field(description="Original user story text as-is from the ticket")

    # 10-criterion scorecard (INVEST + GDS extensions)
    criteria_scores: list[CriterionScore] = Field(
        description="Score and RAG status for each of the 10 criteria",
        min_length=10,
        max_length=10,
    )
    initial_total: int = Field(description="Sum of initial scores (10–100)")

    # Enhanced story
    enhanced_story: str = Field(
        description="Rewritten user story incorporating all recommendations — targets 10/10 per criterion"
    )
    enhanced_criteria_scores: list[CriterionScore] = Field(
        description="Re-evaluated scores for the enhanced story",
        min_length=10,
        max_length=10,
    )
    final_total: int = Field(description="Sum of final scores after enhancement (10–100)")

    overall_recommendation: Recommendation = Field(
        description="Approve (≥80) / Refine (50–79) / Reject (<50) based on initial_total"
    )
    summary: str = Field(
        description="2–3 sentence executive summary of key gaps and what the BA should address"
    )
    timestamp: str = Field(description="ISO 8601 timestamp of the assessment")
