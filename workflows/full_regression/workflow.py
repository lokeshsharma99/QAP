"""
Full Regression Workflow
=========================

The complete local-run → analyse → heal → push loop.

Pipeline
--------
  1. Run Regression Suite    (Engineer → run_tests → parse_test_report)
  2. All Green?
     ├── YES → Push to Azure DevOps + Trigger Pipeline
     └── NO  →
          3. Notify Teams + Slack — HITL gate  (Detective)
          4. Analyse Failures                  (Detective → RCAReport)
          5. Healable?
             ├── LOCATOR_STALE + confidence ≥ 0.99 →
             │    6. Medic patches locator
             │    7. Healing Judge validates patch
             │    8. Re-run tests (verify 3×)
             │    9. Librarian indexes learnings
             │   10. Re-run full suite → if green → push to ADO
             └── ELSE (LOGIC_CHANGE / low confidence) →
                  Human Lead escalation via /approvals
"""

import re

from agno.workflow import Condition, Loop, OnError, Step, Workflow

from agents.detective import detective
from agents.engineer import engineer
from agents.healing_judge import healing_judge
from agents.librarian import librarian
from agents.medic import medic


# ---------------------------------------------------------------------------
# Condition gates
# ---------------------------------------------------------------------------

def suite_is_green(step_input) -> bool:
    """True when the test report shows zero failures."""
    content = str(step_input.previous_step_content or "")
    return (
        '"status": "PASS"' in content
        or "status: PASS" in content
        or ("PASS" in content and "failed: 0" in content.lower())
    )


def failure_is_healable(step_input) -> bool:
    """True when Detective classifies the failure as LOCATOR_STALE with confidence ≥ 0.99."""
    content = str(step_input.previous_step_content or "").lower()
    has_locator_stale = "locator_stale" in content
    match = re.search(r'confidence["\s:]+([0-9.]+)', content)
    confidence = float(match.group(1)) if match else 0.0
    return has_locator_stale and confidence >= 0.99


def patch_is_validated(step_input) -> bool:
    """True when Healing Judge approves the patch (confidence ≥ 0.99, selector-only)."""
    content = str(step_input.previous_step_content or "").lower()
    approved = "approved" in content or "is_valid" in content or "passed" in content
    match = re.search(r'confidence["\s:]+([0-9.]+)', content)
    confidence = float(match.group(1)) if match else 0.0
    return approved and confidence >= 0.99


# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
full_regression = Workflow(
    id="full-regression",
    name="Full Regression Loop",
    description=(
        "Run automation/ → parse report → if failures: Detective RCA → "
        "Medic heal → retest → if all green: push to Azure DevOps + trigger pipeline"
    ),
    steps=[
        # -------------------------------------------------------------------
        # Step 1 — Run the full regression suite and parse results
        # -------------------------------------------------------------------
        Step(
            name="Run Regression Suite",
            agent=engineer,
            description="""Execute the full Cucumber/Playwright regression suite and parse the report.

Your task:
1. Call run_tests() — this runs `npm run test:regression` in automation/.
   Pass tags="" to run the full suite, or a tag expression like "@smoke" for a subset.
2. The tool writes results to automation/reports/cucumber-report.json automatically.
3. Call parse_test_report() to extract pass/fail counts and failure details.
4. Output the full report dict including: status, passed, failed, total, failures list.

Output format (MUST include):
  status: PASS | FAIL
  passed: <n>
  failed: <n>
  total: <n>
  failures: [{feature, scenario, step, error}, ...]
  html_report: <path>

Do NOT proceed if run_tests returns an ERROR — fix the setup issue first.""",
        ),
        # -------------------------------------------------------------------
        # Branch A: all green → push to Azure DevOps
        # -------------------------------------------------------------------
        Condition(
            name="Green Gate — Push to ADO",
            evaluator=suite_is_green,
            steps=[
                Step(
                    name="Push to Azure DevOps",
                    agent=engineer,
                    description="""All tests passed. Push the automation code to Azure DevOps and trigger the CI pipeline.

Your task:
1. Use GitHub MCP (or ADO MCP) tools to:
   a. Create a feature branch: feat/regression-<ISO-date>
   b. Commit all changed files under automation/ with message:
      "test: regression suite green — <passed> scenarios passed"
   c. Push the branch to Azure DevOps.
   d. Create a Pull Request targeting the main branch.
   e. Trigger the ADO pipeline for the main branch (use pipelines domain).
2. Output:
   - branch_name
   - pr_url
   - pipeline_run_id
   - message: "Regression suite green. PR created and ADO pipeline triggered."

Do NOT push if any test is still failing.""",
                ),
            ],
        ),
        # -------------------------------------------------------------------
        # Branch B: failures → notify + triage + heal loop
        # -------------------------------------------------------------------
        Condition(
            name="Failure Branch — Triage & Heal",
            evaluator=lambda s: not suite_is_green(s),
            steps=[
                # Step 2 — Notify Teams + Slack (HITL gate)
                Step(
                    name="Notify Teams & Slack — Await HITL",
                    agent=detective,
                    description="""The regression suite has failures. Notify the team and await Human Lead approval before triaging.

Your task:
1. From the Run Regression Suite output, extract the failures list.
2. Format a summary: total failed, scenario names, error snippets.
3. Call post_rca_to_teams with:
   - test_name: "Full Regression Suite"
   - classification: "REGRESSION_FAILURE"
   - confidence: 1.0
   - root_cause: summary of failures
   - affected_file: "automation/ (multiple)"
   - suggested_fix: "Detective will triage. Medic will heal LOCATOR_STALE failures."
   - requires_human: False
4. Call post_rca_to_slack with the same values.
5. Both calls will pause for Human Lead confirmation (requires_confirmation=True).
6. After approval, output: "Team notified. Proceeding to failure triage."

Do NOT proceed until both confirmations are received.""",
                ),
                # Step 3 — Detective analyses each failure
                Step(
                    name="Analyse Failures",
                    agent=detective,
                    description="""Analyse each failed test scenario and produce an RCAReport for each.

Input: failures list from the Run Regression Suite step.

Your task:
1. For each failure in the list:
   a. Parse the error message and step context.
   b. If a trace.zip is available in automation/test-results/, call parse_trace_zip() on it.
   c. Call classify_failure() to classify:
      LOCATOR_STALE | DATA_MISMATCH | TIMING_FLAKE | ENV_FAILURE | LOGIC_CHANGE
   d. Set confidence (0.0–1.0) and requires_human (True if LOGIC_CHANGE).
2. Output ALL RCAReports in a list. Each must have:
   - test_name, classification, confidence, root_cause,
     affected_file, affected_locator (if LOCATOR_STALE), suggested_fix, requires_human

Priority: LOCATOR_STALE failures with confidence ≥ 0.99 are auto-healable by Medic.""",
                ),
                # Step 4 — Heal loop for each healable failure
                Condition(
                    name="Healable Check",
                    evaluator=failure_is_healable,
                    steps=[
                        Loop(
                            name="Heal Loop",
                            max_iterations=3,
                            steps=[
                                Step(
                                    name="Patch Locator",
                                    agent=medic,
                                    description="""Apply a surgical locator patch to the failing POM.

Input: RCAReport with classification=LOCATOR_STALE.

Your task:
1. Read automation/pages/<affected_file>.
2. Find the exact locator line matching affected_locator.
3. Replace ONLY that line with the suggested_fix locator.
4. Write the patched file back to automation/pages/<affected_file>.
5. Produce a HealingPatch with: old_locator, new_locator, diff (≤5 lines).

CRITICAL: Change exactly ONE locator. Zero logic changes. Zero method renames.""",
                                ),
                                Step(
                                    name="Validate Patch",
                                    agent=healing_judge,
                                    on_error=OnError.pause,
                                    description="""Validate the HealingPatch is surgical and safe.

Input: HealingPatch from Patch Locator step.

Your task:
1. Verify: only locator selectors changed (data-testid, role, text).
2. Verify: diff is ≤ 5 lines.
3. Verify: no assertions, method names, or business logic changed.
4. Score confidence 0.0–1.0.

Approve only if confidence ≥ 0.99. If < 0.99, pause for Human Lead via /approvals.""",
                                ),
                                Condition(
                                    name="Patch Validated",
                                    evaluator=patch_is_validated,
                                    steps=[
                                        Step(
                                            name="Retest After Heal",
                                            agent=engineer,
                                            description="""Re-run the specific failing test 3 times to confirm the patch is stable.

Input: HealingPatch with affected test scenario name/tag.

Your task:
1. Call run_tests() targeting the specific scenario tag or feature file.
2. Repeat 3 times. All 3 must pass.
3. Call parse_test_report() after each run.
4. If any run fails: output RETEST_FAILED — the Loop will retry with Medic.
5. If all 3 pass: output RETEST_PASSED with verification_passes: 3.

Output: RETEST_PASSED or RETEST_FAILED.""",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        # After heal loop — index learnings and re-run full suite
                        Step(
                            name="Index Healing Learnings",
                            agent=librarian,
                            description="""Store the healing pattern in the knowledge base for future reference.

Input: RCAReport + HealingPatch + retest results.

Your task:
1. Index the healing pattern: old locator → new locator, AUT page, date.
2. Update the site_manifesto KB with the corrected locator.
3. Add to qap_learnings KB: "LOCATOR_STALE on <page>: <old> → <new>"
4. Output: number of documents indexed, KB tables updated.""",
                        ),
                        # Final re-run of the full suite after healing
                        Step(
                            name="Full Suite Re-run After Healing",
                            agent=engineer,
                            description="""Re-run the complete regression suite to confirm all healed tests now pass.

Your task:
1. Call run_tests() — full suite, no tag filter.
2. Call parse_test_report().
3. If status is PASS: output "Full regression green after healing. Ready to push."
4. If status is FAIL: list remaining failures. Do NOT push.

Output the full report dict.""",
                        ),
                        # If suite is now green — push to ADO
                        Condition(
                            name="Post-Heal Green Gate",
                            evaluator=suite_is_green,
                            steps=[
                                Step(
                                    name="Push Healed Code to Azure DevOps",
                                    agent=engineer,
                                    description="""All tests now pass after healing. Push the healed automation to Azure DevOps.

Your task:
1. Create branch: fix/heal-locators-<ISO-date>
2. Commit all changed POM files under automation/pages/ with message:
   "fix: heal stale locators — <n> locators patched, regression green"
3. Push to Azure DevOps.
4. Create Pull Request targeting main.
5. Trigger the ADO pipeline on the branch.
6. Output: branch_name, pr_url, pipeline_run_id.""",
                                ),
                            ],
                        ),
                    ],
                ),
                # Non-healable failures → escalate to Human Lead
                Condition(
                    name="Human Escalation Gate",
                    evaluator=lambda s: not failure_is_healable(s),
                    steps=[
                        Step(
                            name="Escalate Non-Healable Failures",
                            agent=detective,
                            description="""The failures cannot be auto-healed (LOGIC_CHANGE or low confidence).
Escalate to Human Lead via the approval queue.

Your task:
1. For each non-healable RCAReport:
   a. Set requires_human: True.
   b. Call post_rca_to_teams with requires_human=True.
   c. Call post_rca_to_slack with requires_human=True.
2. Write a summary to the Human Lead:
   - Which tests failed
   - Why they cannot be auto-healed
   - Recommended manual action
3. The run pauses here. Human Lead must triage manually, fix the code,
   and re-trigger this workflow after the fix.

Output: Escalation summary with all RCAReports that need human attention.""",
                        ),
                    ],
                ),
            ],
        ),
    ],
)
