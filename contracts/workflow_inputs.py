"""
Workflow Input Contracts
========================

Pydantic models used as `input_schema=` on Workflow constructors.
Validates data at the system boundary before workflow execution begins.

Usage:
    workflow.run(input=JiraTicketInput(ticket_id="GDS-5"))
    workflow.run(input={"ticket_id": "GDS-5"})  # dict form also accepted
"""

from pydantic import BaseModel, Field


class JiraTicketInput(BaseModel):
    """Input contract for workflows triggered by a Jira ticket.

    Used by: jira_to_pr, spec_to_code, grooming
    """

    ticket_id: str = Field(description="Jira ticket ID (e.g. GDS-5, QAP-123)")
    description: str = Field(
        default="",
        description="Optional plain-text requirement or additional context",
    )


class TriageInput(BaseModel):
    """Input contract for the Triage & Heal workflow.

    Used by: triage_heal
    """

    test_name: str = Field(description="The failing test name or scenario ID")
    trace_zip_path: str | None = Field(
        default=None,
        description="Absolute path to the Playwright trace.zip for the failed test",
    )
    log_content: str = Field(
        default="",
        description="CI/CD log output to include in the RCA (stdout/stderr from the run)",
    )
    rca_hint: str = Field(
        default="",
        description=(
            "Optional pre-classification hint to guide the Detective "
            "(e.g. 'LOCATOR_STALE', 'DATA_MISMATCH')"
        ),
    )


class DiscoveryInput(BaseModel):
    """Input contract for the Discovery Onboard workflow.

    Used by: discovery_onboard
    """

    aut_url: str = Field(
        description="Base URL of the Application Under Test to crawl (e.g. https://example.com)"
    )
    max_pages: int = Field(
        default=20,
        description="Maximum number of pages to crawl (default 20)",
    )
