"""
contracts/pipeline_rca_report.py
==================================

PipelineRCAReport — the Pipeline Analyst agent's output contract.

Produced by: Pipeline Analyst
Consumed by: Medic (locator fixes), Engineer (script fixes),
             Data Agent (data fixes), Judge (quality gate),
             Scribe (update Gherkin if ACs changed).
"""

from pydantic import BaseModel, Field


class RemediationStep(BaseModel):
    """A single concrete action to resolve the pipeline failure."""

    step_number: int
    """Execution order — steps should be performed in ascending order."""

    action: str
    """
    Human-readable description of the action to take.
    Examples:
      'Update data-testid in UniversalCreditWizardPage.ts line 42 from
       "dob-day-input" to "date-of-birth-day"'
      'Re-run the failed workflow to rule out transient env failure'
      'Open PR to update GDS-Dashboard.feature — step text no longer matches
       the renamed button label'
    """

    responsible_agent: str
    """
    Which agent or person should execute this step.
    Values: 'Medic' | 'Engineer' | 'Data Agent' | 'Scribe' | 'Detective' |
            'DevOps' | 'Human Lead' | 'QA Engineer'
    """

    command: str | None = None
    """
    Optional concrete command, code snippet, or API call to run.
    Examples:
      'npx playwright test --grep "Universal Credit" --headed'
      'git diff HEAD~1 -- automation/pages/UniversalCreditWizardPage.ts'
      'sed -i "s/dob-day-input/date-of-birth-day/g" automation/pages/UniversalCreditWizardPage.ts'
    """

    file_path: str | None = None
    """Specific file to edit (if applicable)."""

    line_hint: str | None = None
    """Approximate line number or code snippet to find in the file."""

    priority: str = "before-next-run"
    """
    When this step must happen:
      immediate      — fix now before any more CI runs (blocks pipeline)
      before-next-run — fix before next scheduled regression run
      backlog         — good-to-have, doesn't block current run
    """

    estimated_effort: str = "< 30 min"
    """Rough time estimate: '< 5 min' | '< 30 min' | '1-2 hours' | '> 1 day'."""


class FailedJob(BaseModel):
    """Details of a single failed CI job."""

    job_name: str
    step_name: str
    """The specific step within the job that failed."""

    error_message: str
    """Extracted error text from the job log."""

    log_url: str | None = None
    """Direct URL to the job log in GitHub Actions."""

    test_name: str | None = None
    """If the failure is a specific test case, its full name."""

    screenshot_url: str | None = None
    """URL to Playwright screenshot artifact if available."""

    trace_url: str | None = None
    """URL to Playwright trace.zip artifact if available."""


class PipelineRCAReport(BaseModel):
    """
    Full pipeline-level RCA for a failed GitHub Actions workflow run.

    The Pipeline Analyst produces this after:
    1. Fetching the workflow run details via GitHub MCP (actions toolset)
    2. Reading the job/step logs to extract failure messages
    3. Correlating the failure with recent commits and PRs
    4. Querying the Automation KB for the affected test code
    5. Classifying the root cause and generating a remediation plan
    """

    # ---------------------------------------------------------------------------
    # Pipeline context
    # ---------------------------------------------------------------------------
    workflow_run_id: str
    """GitHub Actions workflow run ID (numeric string)."""

    workflow_name: str
    """Name of the workflow (e.g., 'CI', 'Regression Suite', 'PR Check')."""

    repository: str
    """Full repo name, e.g., 'lokeshsharma99/GDS-Demo-App'."""

    branch: str = "main"
    """Branch the run was triggered on."""

    trigger: str = "push"
    """What triggered the run: 'push' | 'pull_request' | 'schedule' | 'manual'."""

    run_url: str = ""
    """Direct URL to the GitHub Actions run."""

    run_attempt: int = 1
    """Which attempt this analysis covers (retries have attempt > 1)."""

    # ---------------------------------------------------------------------------
    # Failure surface
    # ---------------------------------------------------------------------------
    failed_jobs: list[FailedJob] = Field(default_factory=list)
    """All jobs that failed in this run."""

    total_tests_run: int = 0
    total_tests_failed: int = 0
    total_tests_passed: int = 0
    total_tests_skipped: int = 0

    # ---------------------------------------------------------------------------
    # Causal correlation
    # ---------------------------------------------------------------------------
    correlated_pr_number: int | None = None
    """PR that triggered or preceded this run (if traceable)."""

    correlated_pr_title: str | None = None
    correlated_commit_sha: str | None = None
    correlated_commit_message: str | None = None
    correlated_author: str | None = None

    changed_files_in_trigger: list[str] = Field(default_factory=list)
    """Files changed in the triggering commit/PR — used to correlate failures."""

    # ---------------------------------------------------------------------------
    # Root cause classification
    # ---------------------------------------------------------------------------
    classification: str
    """
    Root cause category:
      FUNCTIONALITY_CHANGE — application behaviour changed, tests are now wrong
      LOCATOR_CHANGE       — UI element moved/renamed, locator is stale (Medic can fix)
      SCRIPT_ERROR         — automation code bug (wrong assertion, bad wait strategy)
      DATA_ISSUE           — test data missing, stale, or colliding
      ENV_FAILURE          — infrastructure: network, DB, container, timeout
      TEST_INFRA           — Playwright / Node / package version issue
      FLAKY_TEST           — non-deterministic pass/fail, needs stability fix
    """

    confidence: float = 0.0
    """Confidence in the classification (0.0–1.0). < 0.7 → requires_human_review."""

    root_cause: str = ""
    """
    Detailed human-readable explanation of the root cause.
    Should include: what failed, why it failed, what evidence supports this.
    """

    evidence: list[str] = Field(default_factory=list)
    """
    List of evidence items supporting the classification.
    Examples:
      'Job log line 347: "Error: locator .login-btn not found"'
      'Commit abc1234 renamed class "LoginPage" to "AuthPage" 2 hours before run'
      'Same test passed in run #1234 but failed in #1235 — first run after PR #89 merge'
    """

    # ---------------------------------------------------------------------------
    # Remediation plan
    # ---------------------------------------------------------------------------
    remediation_steps: list[RemediationStep] = Field(default_factory=list)
    """
    Ordered, concrete steps to resolve the failure.
    Step 1 should always be achievable in the shortest time possible (quick wins first).
    Include steps for immediate fix AND steps to prevent recurrence.
    """

    # ---------------------------------------------------------------------------
    # Meta
    # ---------------------------------------------------------------------------
    regression_risk: str = "medium"
    """
    Impact of this failure on the release:
      low      — isolated flaky test, not on critical path
      medium   — feature coverage gap, release possible with known risk
      high     — critical path broken, do not release
      critical — multiple critical paths broken, immediate rollback required
    """

    summary: str = ""
    """
    Executive summary for the team (3-5 sentences).
    Should state: what broke, why, confidence level, and the top 2 remediation steps.
    """

    requires_human_review: bool = False
    """True if confidence < 0.7 or classification is FUNCTIONALITY_CHANGE."""

    estimated_fix_time: str = "< 30 min"
    """Overall estimated time to apply all remediation steps."""

    auto_healable: bool = False
    """True if classification is LOCATOR_CHANGE and Medic can fix it autonomously."""
