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


class ImpactAssessmentInput(BaseModel):
    """Input contract for the Impact Assessment workflow.

    Used by: impact_assessment

    Supports GitHub PRs, GitHub Issues, Jira tickets, and ADO work items.
    At least one of pr_number, issue_number, jira_ticket_id, or ado_work_item_id
    must be provided.
    """

    pr_number: int | None = Field(
        default=None,
        description="GitHub Pull Request number to analyse (e.g. 42)",
    )
    issue_number: int | None = Field(
        default=None,
        description="GitHub Issue number to analyse (e.g. 15)",
    )
    jira_ticket_id: str | None = Field(
        default=None,
        description="Jira ticket ID to fetch acceptance criteria from (e.g. GDS-5, QAP-42)",
    )
    ado_work_item_id: int | None = Field(
        default=None,
        description="Azure DevOps work item ID to fetch ACs from (e.g. 1234)",
    )
    repo: str = Field(
        default="",
        description=(
            "GitHub repo in owner/name format. Defaults to the AUT repo set in env "
            "(AUT_GITHUB_OWNER / AUT_GITHUB_REPO)."
        ),
    )
    additional_context: str = Field(
        default="",
        description="Optional plain-text context to help the Impact Analyst (e.g. 'focus on checkout flow')",
    )


class PipelineFailureInput(BaseModel):
    """Input contract for the Pipeline Failure Assessment workflow.

    Used by: pipeline_failure_assessment

    Supports GitHub Actions and Azure DevOps pipeline failures.
    Provide run_id for a specific run, or leave blank to diagnose the latest
    failed run for the configured AUT repo.
    """

    run_id: int | None = Field(
        default=None,
        description="GitHub Actions workflow run ID to diagnose (e.g. 12345678). "
                    "Leave blank to use the latest failed run.",
    )
    ado_build_id: int | None = Field(
        default=None,
        description="Azure DevOps build / pipeline run ID to diagnose (e.g. 567).",
    )
    repo: str = Field(
        default="",
        description=(
            "GitHub repo in owner/name format. Defaults to the AUT repo set in env "
            "(AUT_GITHUB_OWNER / AUT_GITHUB_REPO)."
        ),
    )
    workflow_name: str = Field(
        default="",
        description="Optional: filter to a specific GitHub Actions workflow name (e.g. 'CI Pipeline')",
    )
    additional_context: str = Field(
        default="",
        description="Optional hint to guide the Pipeline Analyst (e.g. 'only started failing on branch X')",
    )
