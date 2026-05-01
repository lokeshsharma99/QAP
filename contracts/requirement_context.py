"""
RequirementContext Contract
============================

Architect agent output — the Execution Plan.
Every pipeline starts here. All acceptance criteria must be captured,
including those sourced from linked requirements.
"""

from pydantic import BaseModel, Field


class AcceptanceCriterion(BaseModel):
    id: str                         # e.g., "AC-001" or "GDS-2-AC-001" for linked tickets
    description: str
    testable: bool
    source_ticket: str = ""         # Originating ticket key (empty = parent ticket)


class LinkedRequirement(BaseModel):
    key: str                        # Jira issue key, e.g. "GDS-2"
    summary: str
    link_type: str                  # e.g. "relates to", "is required by"
    status: str                     # Jira status of the linked issue
    url: str = ""


class RequirementContext(BaseModel):
    """Also referred to as the 'Execution Plan' — the Architect's output."""

    ticket_id: str                          # Jira/ADO ticket ID
    title: str
    description: str
    acceptance_criteria: list[AcceptanceCriterion]
    linked_requirements: list[LinkedRequirement] = Field(default_factory=list)
    priority: str                           # P0, P1, P2, P3
    component: str                          # e.g., "checkout", "auth", "dashboard"
    source_url: str                         # Link to original ticket
    affected_page_objects: list[str]        # POMs the Architect determined will be affected
    is_new_feature: bool                    # True if no existing coverage found in KB
