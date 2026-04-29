"""
Jira-to-PR Workflow
====================

Full pipeline: Jira ticket → Architect → Scribe → [Gherkin Judge Gate]
→ Data Agent → Engineer → [Code Judge Gate] → GitHub PR.

Pipeline:
  1. Fetch Jira Ticket   (Architect → RequirementContext)
  2. Author Gherkin Spec (Scribe    → GherkinSpec)
  3. Gherkin Judge Gate  (Judge     → JudgeVerdict)  ⚖️  ≥90% auto / <90% human
  4. Provision Test Data (Data Agent → RunContext)
  5. Generate Code       (Engineer  → POM + StepDefs)
  6. Code Judge Gate     (Judge     → JudgeVerdict)  ⚖️  ≥90% auto / <90% human
  7. Submit GitHub PR    (Engineer  → PR URL)        ✅  auto on approval
"""

import re

from agno.workflow import Condition, Step, Workflow

from agents.architect import architect
from agents.data_agent import data_agent
from agents.engineer import engineer
from agents.judge import judge
from agents.scribe import scribe


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _confidence(content: str) -> float:
    """Extract confidence from a JudgeVerdict JSON block in agent output."""
    m = re.search(r'"confidence":\s*([\d.]+)', content)
    return float(m.group(1)) if m else 0.0


def gherkin_verdict_passes(step_input) -> bool:  # type: ignore[no-untyped-def]
    """Gate: auto-approve Gherkin spec when Judge confidence >= 0.90."""
    content = str(getattr(step_input, "previous_step_content", "") or "")
    explicit_pass = bool(re.search(r'"passed":\s*true', content, re.IGNORECASE))
    return explicit_pass or _confidence(content) >= 0.90


def code_verdict_passes(step_input) -> bool:  # type: ignore[no-untyped-def]
    """Gate: auto-approve automation code when Judge confidence >= 0.90."""
    content = str(getattr(step_input, "previous_step_content", "") or "")
    explicit_pass = bool(re.search(r'"passed":\s*true', content, re.IGNORECASE))
    return explicit_pass or _confidence(content) >= 0.90


# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
jira_to_pr = Workflow(
    id="jira-to-pr",
    name="Jira to PR Pipeline",
    steps=[
        # -------------------------------------------------------------------
        # Step 1 — Architect: parse Jira ticket → RequirementContext
        # -------------------------------------------------------------------
        Step(
            name="Fetch Jira Ticket",
            agent=architect,
            description="""As the Architect, analyze the Jira ticket provided in the input and produce a RequirementContext.

Input: Jira ticket ID (e.g. "QAP-123") or a plain-text requirement description.

Your task:
1. If a ticket ID is provided, fetch the full ticket details via Jira/ADO MCP tools.
2. Extract all acceptance criteria — every AC must be testable and uniquely identified (AC-001, AC-002, …).
3. Identify affected Page Objects by querying the automation knowledge base.
4. Classify priority (P0–P3) and the component (e.g. "checkout", "auth", "dashboard").
5. Set is_new_feature=True if no existing coverage is found in the knowledge base.

Output: RequirementContext — ticket_id, title, description, acceptance_criteria,
priority, component, source_url, affected_page_objects, is_new_feature.""",
        ),
        # -------------------------------------------------------------------
        # Step 2 — Scribe: RequirementContext → GherkinSpec (.feature file)
        # -------------------------------------------------------------------
        Step(
            name="Author Gherkin Spec",
            agent=scribe,
            description="""As the Scribe, convert the RequirementContext into a Gherkin specification.

Input: RequirementContext from the previous step.

Your task:
1. Map every acceptance criterion (AC-001 … AC-N) to at least one Gherkin Scenario.
2. Use Given / When / Then structure. Add Scenario Outline + Examples for data-driven cases.
3. Identify test data requirements (fields, types, constraints, PII masking).
4. Populate traceability: each Scenario name must reference its AC ID.
5. Set feature_file to the canonical path: automation/features/<component>/<ticket_id>.feature

Output: GherkinSpec — feature_name, feature_content (full .feature text),
data_requirements, traceability map, feature_file path.""",
        ),
        # -------------------------------------------------------------------
        # Step 3 — Judge: validate GherkinSpec  ⚖️  ≥90% → auto / <90% → human
        # -------------------------------------------------------------------
        Step(
            name="Gherkin Quality Gate",
            agent=judge,
            description="""As the Judge, perform an adversarial review of the GherkinSpec.

Input: GherkinSpec from the previous step.

Run the full DoD checklist:
- Every AC from the RequirementContext has at least one matching Scenario.
- All scenarios use Given / When / Then with no ambiguous steps.
- Scenario Outlines have a populated Examples table.
- No hardcoded wait times or implementation details in step text.
- traceability map is complete (every AC-ID appears in at least one Scenario name).
- data_requirements list every field used in Scenario Outlines.
- feature_file path matches the pattern automation/features/<component>/<ticket_id>.feature

Score confidence 0.0–1.0:
  ≥ 0.90 → set passed=true, requires_human=false  (pipeline continues automatically)
  < 0.90 → set passed=false, requires_human=true   (pipeline pauses for Human Lead)
  < 0.50 → set passed=false, requires_human=true   (auto-reject, list all blocking issues)

Output: JudgeVerdict — artifact_type="gherkin", confidence, passed, checklist_results,
rejection_reasons, requires_human.""",
        ),
        # -------------------------------------------------------------------
        # Condition: only continue if Judge approved (confidence >= 0.90)
        # -------------------------------------------------------------------
        Condition(
            name="Gherkin Approved",
            evaluator=gherkin_verdict_passes,
            steps=[
                # -----------------------------------------------------------
                # Step 4 — Data Agent: GherkinSpec → RunContext (test fixtures)
                # -----------------------------------------------------------
                Step(
                    name="Provision Test Data",
                    agent=data_agent,
                    description="""As the Data Agent, provision synthetic test data for the approved GherkinSpec.

Input: GherkinSpec (with data_requirements) from the Gherkin Quality Gate step.

Your task:
1. Create synthetic TestUser records for every role referenced in the scenarios.
2. Generate db_seed_queries to insert required test records (no real PII).
3. Populate api_mocks for any third-party endpoints called in the scenarios.
4. Generate cleanup_queries that are the exact inverse of seed_queries.
5. Verify unique constraints — no duplicate emails, usernames, or IDs.
6. Set pii_masked=True and unique_constraints_valid=True.

Output: RunContext — ticket_id, test_users, db_seed_queries, api_mocks,
cleanup_queries, pii_masked, unique_constraints_valid.""",
                ),
                # -----------------------------------------------------------
                # Step 5 — Engineer: RunContext → POM + Step Definitions
                # -----------------------------------------------------------
                Step(
                    name="Generate Automation Code",
                    agent=engineer,
                    description="""As the Engineer, write Playwright automation code for the approved GherkinSpec.

Input: RunContext from the previous step.  Also reference the GherkinSpec from the
Gherkin Quality Gate step and the RequirementContext from the Fetch Jira Ticket step.

Look-Before-You-Leap protocol (MANDATORY):
1. Query the Site Manifesto knowledge base for current locators on the affected pages.
2. Query the automation knowledge base for existing POMs and step definitions.
3. Only create new files — never duplicate existing Page Object classes.

Then produce:
- Page Object(s) in automation/pages/<component>/<PageName>.ts
  • All locators use data-testid, role, or text strategies — NO CSS or XPath.
  • Every public method has a JSDoc comment.
- Step Definitions in automation/step_definitions/<component>/<ticket_id>.steps.ts
  • Map every Given / When / Then step from the feature file to an implementation.
  • Use Playwright auto-waiting — NO sleep() or waitForTimeout().
- Update automation/features/<component>/<ticket_id>.feature if the file does not exist.

Output: Paths of all files written, a brief description of each class/method, and
the branch name created (feat/<ticket_id>).""",
                ),
                # -----------------------------------------------------------
                # Step 6 — Judge: validate code  ⚖️  ≥90% → auto / <90% → human
                # -----------------------------------------------------------
                Step(
                    name="Code Quality Gate",
                    agent=judge,
                    description="""As the Judge, perform an adversarial review of the automation code.

Input: Engineer output from the previous step (file paths + code content).

Read each generated file and run the full DoD checklist:
- All locators use data-testid / role / text — reject any CSS selector or XPath.
- No sleep(), waitForTimeout(), or fixed numeric timeouts.
- Every step from the .feature file has a matching step definition.
- Page Object methods match the locators in the Site Manifesto.
- No hardcoded secrets, credentials, or environment URLs.
- TypeScript compiles without errors (run_typecheck tool must pass).
- No duplicate class definitions with existing POMs in the knowledge base.

Score confidence 0.0–1.0:
  ≥ 0.90 → set passed=true, requires_human=false  (PR auto-submitted)
  < 0.90 → set passed=false, requires_human=true   (pipeline pauses for Human Lead)
  < 0.50 → set passed=false, requires_human=true   (auto-reject, list all blocking issues)

Output: JudgeVerdict — artifact_type="code", confidence, passed, checklist_results,
rejection_reasons, requires_human.""",
                ),
                # -----------------------------------------------------------
                # Condition: only submit PR if code Judge approved
                # -----------------------------------------------------------
                Condition(
                    name="Code Approved",
                    evaluator=code_verdict_passes,
                    steps=[
                        # ---------------------------------------------------
                        # Step 7 — Engineer: auto-submit GitHub PR
                        # ---------------------------------------------------
                        Step(
                            name="Submit GitHub PR",
                            agent=engineer,
                            description="""As the Engineer, create a GitHub Pull Request for the automation code.

Input: All prior step outputs — branch name (feat/<ticket_id>) was created in the
Generate Automation Code step.

Your task using GitHub MCP tools:
1. Confirm the branch feat/<ticket_id> exists and has the generated files committed.
   If files are not yet committed, stage and commit them now:
   - Commit message: "feat(<component>): add automation for <ticket_id> — <title>"
2. Push the branch to origin if not already pushed.
3. Open a Pull Request:
   - base: main
   - head: feat/<ticket_id>
   - title: "feat(<component>): <ticket_id> — <title>"
   - body: include the feature file content, RunContext summary, and JudgeVerdict summary.
   - Labels: ["automation", "qa", "<component>"]
4. Return the PR URL and PR number.

Output: PR URL, PR number, branch name, commit SHA.""",
                        ),
                    ],
                ),
            ],
        ),
    ],
)
