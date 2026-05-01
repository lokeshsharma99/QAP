"""
Spec-to-Code Workflow
=====================

Requirement (Jira) → Architect → Scribe → [Gherkin Judge Gate] → Data Agent → Engineer → [Code Judge Gate] → PR

Pipeline:
  1. Parse Requirements (Architect)
  2. Author Gherkin (Scribe)
  3. Gherkin Quality Gate (Judge — produces JudgeVerdict, ≥90% auto / <90% human)
  4. Gherkin Approved (Condition — reads JudgeVerdict confidence)
  5. Provision Data (Data Agent)
  6. Generate Code (Engineer)
  7. Code Quality Gate (Judge — produces JudgeVerdict, ≥90% auto / <90% human)
  8. Code Approved (Condition — reads JudgeVerdict confidence)
  9. Submit PR (Engineer)
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
spec_to_code = Workflow(
    id="spec-to-code",
    name="Requirement to Automation",
    description="Requirement → Architect → Scribe → [Gherkin Judge Gate] → Data Agent → Engineer → [Code Judge Gate] → PR",
    steps=[
        Step(name="Parse Requirements", agent=architect),
        Step(name="Author Gherkin", agent=scribe),
        # ------------------------------------------------------------------
        # Judge reviews the GherkinSpec against the DoD checklist.
        # Outputs JudgeVerdict with confidence 0.0–1.0.
        # ≥0.90 → auto-approve; <0.90 → human review required.
        # ------------------------------------------------------------------
        Step(
            name="Gherkin Quality Gate",
            agent=judge,
            description="""As the Judge, perform an adversarial review of the GherkinSpec.

Run the full DoD checklist:
- Every AC from the RequirementContext has at least one matching Scenario.
- All scenarios use Given / When / Then with no ambiguous steps.
- Scenario Outlines have a populated Examples table.
- No hardcoded wait times or implementation details in step text.
- traceability map is complete (every AC-ID appears in at least one Scenario name).
- data_requirements list every field used in Scenario Outlines.

Score confidence 0.0–1.0:
  ≥ 0.90 → set passed=true, requires_human=false
  < 0.90 → set passed=false, requires_human=true
  < 0.50 → set passed=false, requires_human=true (auto-reject, list all blocking issues)

Output: JudgeVerdict — artifact_type="gherkin", confidence, passed, checklist_results,
rejection_reasons, requires_human.""",
        ),
        Condition(
            name="Gherkin Approved",
            evaluator=gherkin_verdict_passes,
            steps=[
                Step(name="Provision Data", agent=data_agent),
                Step(
                    name="Generate Code",
                    agent=engineer,
                    description="""As the Engineer, write Playwright automation code (Look-Before-You-Leap).

1. Query the Site Manifesto KB for current locators on affected pages.
2. Query the automation KB for existing POMs and step definitions.
3. Only create new files — never duplicate existing Page Object classes.

Produce:
- Page Object(s) in automation/pages/<component>/<PageName>.ts
  · All locators use data-testid, role, or text strategies — NO CSS or XPath.
- Step Definitions in automation/step_definitions/<component>/<ticket_id>.steps.ts
  · Map every Given / When / Then to an implementation.
  · Use Playwright auto-waiting — NO sleep() or waitForTimeout().""",
                ),
                # -----------------------------------------------------------
                # Judge reviews generated code before PR is opened.
                # -----------------------------------------------------------
                Step(
                    name="Code Quality Gate",
                    agent=judge,
                    description="""As the Judge, perform an adversarial review of the automation code.

Read each generated file and run the full DoD checklist:
- All locators use data-testid / role / text — reject any CSS selector or XPath.
- No sleep(), waitForTimeout(), or fixed numeric timeouts.
- Every step from the .feature file has a matching step definition.
- No hardcoded secrets, credentials, or environment URLs.
- No duplicate class definitions with existing POMs in the knowledge base.

Score confidence 0.0–1.0:
  ≥ 0.90 → set passed=true, requires_human=false
  < 0.90 → set passed=false, requires_human=true

Output: JudgeVerdict — artifact_type="code", confidence, passed, checklist_results,
rejection_reasons, requires_human.""",
                ),
                Condition(
                    name="Code Approved",
                    evaluator=code_verdict_passes,
                    steps=[
                        Step(
                            name="Submit PR",
                            agent=engineer,
                            description="""As the Engineer, create a GitHub Pull Request for the automation code.

1. Confirm the feature branch exists with the generated files committed.
   If not committed, stage and commit: "feat(<component>): add automation for <ticket_id>"
2. Push the branch to origin if not already pushed.
3. Open a Pull Request (base: main) with the feature file, RunContext summary,
   and JudgeVerdict summary in the PR body.
4. Return the PR URL and PR number.""",
                        ),
                    ],
                ),
            ],
        ),
    ],
)
