"""
contracts/impact_report.py
==========================

ImpactReport — the Impact Analyst agent's output contract.

Produced by: Impact Analyst
Consumed by: Engineer (to generate/update tests), Scribe (to update .feature files),
             Judge (to gate the regression suite update PR).
"""

from pydantic import BaseModel, Field


class TestGap(BaseModel):
    """A single gap identified in the test suite relative to a code change."""

    type: str
    """
    Category of gap:
      missing_coverage — new feature/code path with no test at all
      obsolete         — test covers a removed or renamed feature (safe to delete)
      needs_update     — test exists but assertions/locators/data are now stale
    """

    description: str
    """Human-readable explanation of the gap and why it matters."""

    related_source_file: str | None = None
    """The changed source file that triggered this gap (relative path in AUT repo)."""

    related_test_file: str | None = None
    """The automation file that needs to be created / updated / deleted."""

    suggested_action: str
    """
    Concrete action for the Engineer or Scribe to take.
    Examples:
      'Add scenario: user can filter by new "In Progress" status in GDS-Dashboard.feature'
      'Remove step definition for deleted LoginPage.submitButton locator'
      'Update data-testid on UniversalCreditWizard step 3 — field renamed to dob-day'
    """

    priority: str = "P2"
    """Severity of the gap: P0 (regression blocker), P1 (high), P2 (normal), P3 (nice-to-have)."""

    acceptance_criterion_ref: str | None = None
    """Reference to the GitHub Issue AC or PR description section this gap maps to."""


class ImpactReport(BaseModel):
    """
    Full impact analysis report for a PR or GitHub Issue.

    The Impact Analyst produces this after:
    1. Reading the PR diff / Issue description via GitHub MCP
    2. Querying the Automation KB for tests covering the changed files
    3. Querying the Site Manifesto for affected UI components
    4. Reasoning about gaps, obsolescence, and staleness
    """

    # ---------------------------------------------------------------------------
    # Source
    # ---------------------------------------------------------------------------
    pr_number: int | None = None
    """GitHub PR number (if triggered by a PR)."""

    issue_number: int | None = None
    """GitHub Issue number (if triggered by an issue)."""

    pr_title: str = ""
    """Title of the PR or Issue that triggered this analysis."""

    pr_url: str = ""
    """URL of the PR or Issue."""

    base_branch: str = "main"
    """The branch the PR targets (usually main)."""

    # ---------------------------------------------------------------------------
    # Change surface
    # ---------------------------------------------------------------------------
    changed_files: list[str] = Field(default_factory=list)
    """All files changed by the PR (relative paths in AUT repo)."""

    changed_source_files: list[str] = Field(default_factory=list)
    """Source files only (excludes test files, docs, configs)."""

    changed_test_files: list[str] = Field(default_factory=list)
    """Test files already changed in the PR (the author did some test work)."""

    # ---------------------------------------------------------------------------
    # Existing coverage
    # ---------------------------------------------------------------------------
    affected_test_files: list[str] = Field(default_factory=list)
    """
    Automation files (in QAP repo) that currently cover the changed source files.
    Found via semantic search on the Automation KB.
    """

    affected_feature_files: list[str] = Field(default_factory=list)
    """Gherkin .feature files whose scenarios exercise the changed functionality."""

    affected_page_objects: list[str] = Field(default_factory=list)
    """Page Object Model files that reference the changed UI components."""

    # ---------------------------------------------------------------------------
    # Gap analysis
    # ---------------------------------------------------------------------------
    test_gaps: list[TestGap] = Field(default_factory=list)
    """
    All identified gaps in the test suite after this change.
    Sorted by priority (P0 first).
    """

    missing_coverage_count: int = 0
    """Number of gaps with type='missing_coverage'."""

    obsolete_count: int = 0
    """Number of gaps with type='obsolete'."""

    needs_update_count: int = 0
    """Number of gaps with type='needs_update'."""

    # ---------------------------------------------------------------------------
    # Verdict
    # ---------------------------------------------------------------------------
    regression_risk: str = "medium"
    """
    Overall regression risk for this change:
      low    — good coverage, no critical gaps
      medium — some gaps, no P0 items
      high   — P0 gaps or obsolete tests that will cause false failures
      critical — breaking changes with zero test coverage
    """

    summary: str = ""
    """Executive summary of the impact analysis (2-5 sentences)."""

    recommended_actions: list[str] = Field(default_factory=list)
    """
    Ordered list of actions for the team to take, e.g.:
      1. 'Create new feature file: features/universal-credit-address.feature'
      2. 'Update locator in UniversalCreditWizardPage.ts line 42 (data-testid changed)'
      3. 'Delete obsolete step definition: step_definitions/old-login.steps.ts'
    """

    confidence: float = 0.0
    """Confidence in this analysis (0.0–1.0). Below 0.7 should trigger human review."""

    requires_human_review: bool = False
    """True if confidence < 0.7 or regression_risk == 'critical'."""
