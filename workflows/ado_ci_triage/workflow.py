"""
ADO CI Triage Workflow
=======================

Azure DevOps pipeline failure → CI Log Analyzer → Judge Gate → route to squad.

Pipeline:
  1. Analyse ADO CI Logs  (CI Log Analyzer → PipelineRCAReport + HITL ADO/Jira ticket)
  2. Judge Quality Gate   (Judge → JudgeVerdict, confidence >= 0.90 auto-approve)
"""

import re

from agno.workflow import Condition, Step, Workflow

from agents.ci_log_analyzer import ci_log_analyzer
from agents.judge import judge


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_confidence(content: str) -> float:
    """Extract confidence score from Judge verdict response."""
    m = re.search(r'"confidence":\s*([\d.]+)', content)
    if m:
        return float(m.group(1))
    pct = re.search(r'[Cc]onfidence[:\s]+(\d+)%', content)
    if pct:
        return float(pct.group(1)) / 100.0
    return 0.0


def judge_approves_rca(step_input) -> bool:  # type: ignore[no-untyped-def]
    """Gate: auto-approve RCA when Judge confidence >= 0.90."""
    content = str(getattr(step_input, "previous_step_content", "") or "")
    explicit_pass = bool(re.search(r'"passed":\s*true', content, re.IGNORECASE))
    return explicit_pass or _extract_confidence(content) >= 0.90


# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
ado_ci_triage = Workflow(
    id="ado-ci-triage",
    name="ADO CI Log Triage",
    description=(
        "Azure DevOps pipeline failure → CI Log Analyzer (RCA + HITL ADO/Jira ticket) "
        "→ Judge quality gate → route to Operations/Engineering/Human Lead"
    ),
    steps=[
        # -------------------------------------------------------------------
        # Step 1 — CI Log Analyzer: fetch logs, classify, HITL ticket creation
        # -------------------------------------------------------------------
        Step(
            name="Analyse ADO CI Logs",
            agent=ci_log_analyzer,
            description="""Analyse the failing Azure DevOps pipeline run and produce a root-cause classification.

Input: ADO pipeline URL or run_id + organisation + project (provided in workflow input).

Your task:
1. Call get_pipeline_runs or use ADO MCP tools to fetch the failed pipeline run details.
2. Read the failing stage/job/step logs to extract the error message.
3. Classify the root cause:
   LOCATOR_CHANGE        — a UI element locator changed in the AUT
   FUNCTIONALITY_CHANGE  — the AUT behaviour changed (real app bug)
   SCRIPT_ERROR          — test code issue (missing import, wrong selector logic)
   DATA_ISSUE            — test data collision or stale seed data
   ENV_FAILURE           — infrastructure issue (Docker, DB, network)
   TEST_INFRA            — CI runner issue (agent pool, timeout, disk)
   FLAKY_TEST            — non-deterministic timing failure
4. Score confidence (0.0 – 1.0).
5. Generate a PipelineRCAReport with ordered remediation steps (responsible_agent on each).
6. After HITL approval: call create_work_item to file an ADO work item OR Atlassian MCP
   to create a Jira bug, depending on the team's configured tracker.

Output: PipelineRCAReport with classification, confidence, remediation_steps, and created ticket reference.""",
        ),
        # -------------------------------------------------------------------
        # Step 2 — Judge Gate: quality review of the RCA
        # -------------------------------------------------------------------
        Condition(
            name="RCA Quality Gate",
            evaluator=judge_approves_rca,
            steps=[
                Step(
                    name="Deliver Approved RCA",
                    agent=judge,
                    description="""The CI Log Analyzer's RCA has sufficient confidence.

Review the PipelineRCAReport against this Definition of Done checklist:
  [ ] classification is one of the 7 valid categories
  [ ] confidence score is justified by the evidence cited
  [ ] all failed jobs are accounted for with error_message
  [ ] remediation_steps are ordered, concrete, and have responsible_agent set
  [ ] requires_human_review is True for FUNCTIONALITY_CHANGE and ENV_FAILURE
  [ ] created ticket reference is present (ADO work item ID or Jira issue key)

Auto-approve at confidence >= 0.90. Output JudgeVerdict with routing recommendation.""",
                ),
            ],
            else_steps=[
                Step(
                    name="Request RCA Refinement",
                    agent=judge,
                    description="""The CI Log Analyzer's RCA confidence is below 0.90.

Review the PipelineRCAReport and provide specific, actionable feedback:
  - Which classification criteria are unclear?
  - Which log evidence is missing?
  - Which remediation steps lack a responsible_agent?

Output JudgeVerdict with rejection_reasons. The workflow will surface this for human review
via the /approvals queue.""",
                ),
            ],
        ),
    ],
)
