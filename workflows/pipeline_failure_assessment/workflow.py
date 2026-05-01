"""
Pipeline Failure Assessment Workflow
======================================

CI failure (GitHub Actions / Azure DevOps) → Pipeline Analyst → Judge Gate
→ Auto-heal dispatch (LOCATOR_CHANGE) OR Human escalation (FUNCTIONALITY_CHANGE)

Phase 1: Diagnostic Data Gathering
  - Fetch failed run details (GitHub Actions or ADO pipeline)
  - Read job logs for summary-level failure info
  - Download CI artifacts (playwright-traces / allure-results) for exact errors
  - Correlate failure with triggering commit / PR / Jira / ADO ticket

Phase 2: Root Cause Analysis & Classification
  - Query Automation KB for the failing test's POM and step definition
  - Classify: LOCATOR_CHANGE / FUNCTIONALITY_CHANGE / SCRIPT_ERROR /
              DATA_ISSUE / ENV_FAILURE / TEST_INFRA / FLAKY_TEST
  - Score confidence (0.0 – 1.0)
  - Generate ordered remediation plan

Phase 3: Quality Gate & Dispatch
  - Judge reviews the PipelineRCAReport
  - confidence >= 0.90 → auto-approve → route to appropriate squad
  - confidence < 0.90  → human review → held in HITL queue
  - LOCATOR_CHANGE + auto_healable → notify Diagnostics Squad (Detective → Medic)
  - FUNCTIONALITY_CHANGE / requires_human_review → escalate to Human Lead
"""

import re

from agno.workflow import Condition, Step, Workflow

from agents.judge import judge
from agents.pipeline_analyst import pipeline_analyst


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _extract_confidence(content: str) -> float:
    """Extract confidence score from agent output."""
    match = re.search(r'"confidence":\s*([\d.]+)', content)
    if match:
        return float(match.group(1))
    pct_match = re.search(r'[Cc]onfidence[:\s]+(\d+)%', content)
    if pct_match:
        return float(pct_match.group(1)) / 100.0
    return 0.0


def _get_classification(content: str) -> str:
    """Extract failure classification from PipelineRCAReport."""
    match = re.search(r'"classification":\s*"([^"]+)"', content)
    return match.group(1) if match else ""


def judge_approves_rca_report(step_input) -> bool:  # type: ignore[no-untyped-def]
    """Gate: only route the report when Judge confidence >= 90%.

    Checks for:
    - Presence of the pipeline_rca_report JSON block
    - Exact error message (not guessed from log)
    - classification and confidence fields are set
    """
    content = str(getattr(step_input, "previous_step_content", "") or "")
    has_report_block = (
        "```pipeline_rca_report" in content or '"classification"' in content
    )
    confidence = _extract_confidence(content)
    requires_human = bool(re.search(r'"requires_human_review":\s*true', content, re.IGNORECASE))
    return has_report_block and confidence >= 0.90 and not requires_human


def is_auto_healable(step_input) -> bool:  # type: ignore[no-untyped-def]
    """Route to Diagnostics Squad if LOCATOR_CHANGE and auto_healable."""
    content = str(getattr(step_input, "previous_step_content", "") or "")
    classification = _get_classification(content)
    confidence = _extract_confidence(content)
    auto_healable = bool(re.search(r'"auto_healable":\s*true', content, re.IGNORECASE))
    return classification == "LOCATOR_CHANGE" and auto_healable and confidence >= 0.85


# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
pipeline_failure_assessment = Workflow(
    id="pipeline-failure-assessment",
    name="CI Pipeline Failure Analysis",
    description=(
        "CI failure (GitHub Actions / Azure DevOps) → Pipeline Analyst → Judge Gate "
        "→ PipelineRCAReport with classification, confidence score, and ordered "
        "remediation plan. Routes LOCATOR_CHANGE to Diagnostics Squad for auto-heal; "
        "escalates FUNCTIONALITY_CHANGE to Human Lead."
    ),
    steps=[
        Step(
            name="Diagnose Pipeline Failure",
            agent=pipeline_analyst,
            description=(
                "Phase 1 — Data Gathering:\n"
                "1. Fetch the failed workflow run (GitHub Actions via `gh_` tools "
                "or Azure DevOps via `ado_` tools). Use the run_id from input if "
                "provided; otherwise fetch the latest failed run.\n"
                "2. Read job logs to identify the failing step and test summary.\n"
                "3. Download CI artifacts: call `download_ci_artifact` for "
                "'playwright-traces' if present, then `parse_junit_xml` for the "
                "exact error. Fall back to 'allure-results' + `parse_allure_results` "
                "if traces artifact is absent.\n"
                "4. Correlate with code changes: fetch the triggering commit/PR diff. "
                "If Jira or ADO tickets are linked, fetch their ACs via `atl_` / `ado_` "
                "tools to distinguish FUNCTIONALITY_CHANGE from SCRIPT_ERROR.\n"
                "\n"
                "Phase 2 — RCA:\n"
                "5. Query Automation KB for the failing test's step definition and POM.\n"
                "6. Classify the failure (LOCATOR_CHANGE / FUNCTIONALITY_CHANGE / "
                "SCRIPT_ERROR / DATA_ISSUE / ENV_FAILURE / TEST_INFRA / FLAKY_TEST).\n"
                "7. Score confidence (0.0-1.0) and set auto_healable / requires_human_review.\n"
                "8. Generate ordered remediation_steps.\n"
                "\n"
                "Output a markdown report followed by a ```pipeline_rca_report JSON block."
            ),
        ),
        Step(
            name="Judge Review",
            agent=judge,
            description=(
                "Review the PipelineRCAReport against the Definition of Done checklist:\n"
                "- [ ] Exact error message was extracted from CI artifact (not guessed)\n"
                "- [ ] Triggering commit / PR is identified with SHA\n"
                "- [ ] Classification is assigned with justification\n"
                "- [ ] Confidence score reflects evidence strength\n"
                "- [ ] remediation_steps are ordered (fastest first)\n"
                "- [ ] auto_healable is True only for LOCATOR_CHANGE with confidence >= 0.85\n"
                "- [ ] requires_human_review is True for FUNCTIONALITY_CHANGE or confidence < 0.7\n"
                "- [ ] responsible_agent is set on every remediation step\n"
                "\n"
                "Respond with a JudgeVerdict containing your confidence score (0.0-1.0). "
                "confidence >= 0.90 → APPROVE. "
                "confidence < 0.90 → list specific deficiencies for the Pipeline Analyst."
            ),
        ),
        Condition(
            name="Judge Gate",
            evaluator=judge_approves_rca_report,
            steps=[
                Condition(
                    name="Route by Classification",
                    evaluator=is_auto_healable,
                    steps=[
                        # LOCATOR_CHANGE + auto_healable path
                        Step(
                            name="Escalate to Diagnostics Squad",
                            agent=pipeline_analyst,
                            description=(
                                "The classification is LOCATOR_CHANGE and the report is "
                                "auto-healable. Produce a handoff summary for the Diagnostics "
                                "Squad (Detective + Medic):\n"
                                "- List all trace.zip artifact paths for the Detective\n"
                                "- Specify the affected PageObject file and suspected stale locator\n"
                                "- Confirm the test name and failure scenario for Medic context\n"
                                "- State that confidence >= 0.85 so auto-heal can proceed\n"
                                "Format as a clear escalation notice with action items."
                            ),
                        ),
                    ],
                    else_steps=[
                        # Non-auto-healable or requires human path
                        Step(
                            name="Escalate to Human Lead",
                            agent=pipeline_analyst,
                            description=(
                                "The classification requires human intervention "
                                "(FUNCTIONALITY_CHANGE, ENV_FAILURE, DATA_ISSUE, or "
                                "requires_human_review=True). Produce a human escalation "
                                "notice:\n"
                                "- Summary of the root cause in plain language\n"
                                "- Why auto-healing is NOT appropriate\n"
                                "- Ordered remediation steps with responsible agent / person\n"
                                "- Any relevant commit SHA, PR link, or Jira/ADO ticket\n"
                                "- Priority: P0 (blocks release) or P1 (fix before next regression run)\n"
                                "Format clearly so the Human Lead can act without further context."
                            ),
                        ),
                    ],
                ),
            ],
            else_steps=[
                Step(
                    name="Refine RCA Report",
                    agent=pipeline_analyst,
                    description=(
                        "The Judge has flagged deficiencies in the PipelineRCAReport. "
                        "Address each deficiency: re-download missing artifacts, "
                        "verify the correlated commit, strengthen classification evidence, "
                        "and re-produce the report. "
                        "Output updated markdown report and ```pipeline_rca_report JSON block."
                    ),
                ),
            ],
        ),
    ],
)
