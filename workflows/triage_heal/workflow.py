"""
Triage-Heal Workflow
=====================

Trace ZIP + Logs → Detective → [Teams HITL Gate] → [Healable Gate] → Medic → Verify 3x

Pipeline:
  1. Analyze Failure   (Detective → RCAReport)
  2. Teams HITL Gate   (Detective → post_rca_to_teams)
     ↳ requires_confirmation=True — surfaces in /approvals AND pauses the chat run.
       Human Lead reviews the Adaptive Card in Teams then approves/rejects in /approvals.
       Both surfaces sync from the same DB record.
  3. Healable Check    (Condition — LOCATOR_STALE + confidence >= 0.99)
  4. Patch Locator     (Medic → HealingPatch)
"""

import re

from agno.workflow import Condition, Loop, Step, Workflow

from agents.detective import detective
from agents.healing_judge import healing_judge
from agents.librarian import librarian
from agents.medic import medic


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_healable(step_input) -> bool:  # type: ignore[no-untyped-def]
    """Gate: only dispatch Medic if failure is LOCATOR_STALE and auto-healable.

    Looks for LOCATOR_STALE classification in the Detective's RCAReport output,
    and verifies that requires_human is not True.
    """
    content = str(getattr(step_input, "previous_step_content", "") or "")
    is_locator_stale = "LOCATOR_STALE" in content
    requires_human = bool(re.search(r'"requires_human":\s*true', content, re.IGNORECASE))
    # Extract confidence if present
    confidence_match = re.search(r'"confidence":\s*([\d.]+)', content)
    confidence = float(confidence_match.group(1)) if confidence_match else 0.0
    return is_locator_stale and not requires_human and confidence >= 0.99


def healing_passed(outputs) -> bool:  # type: ignore[no-untyped-def]
    """End the heal loop early if HealingPatch reports verification_passes >= 3."""
    for output in outputs:
        content = str(getattr(output, "content", "") or "")
        match = re.search(r'"verification_passes":\s*(\d+)', content)
        if match and int(match.group(1)) >= 3:
            return True
    return False


# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
triage_heal = Workflow(
    id="triage-heal",
    name="Failure Triage & Self-Heal",
    description="Trace ZIP + Logs → Detective → [Teams HITL Gate] → [Healable Gate] → Medic → Verify 3x",
    steps=[
        # -------------------------------------------------------------------
        # Step 1 — Detective: parse trace/logs → RCAReport
        # -------------------------------------------------------------------
        Step(name="Analyze Failure", agent=detective),
        # -------------------------------------------------------------------
        # Step 2 — Teams HITL Gate
        # Detective calls post_rca_to_teams (requires_confirmation=True).
        # Agno writes one approval record and pauses. The Human Lead sees:
        #   • An Adaptive Card in the Teams channel (via Power Automate flow)
        #   • An approval card in /approvals
        #   • A paused run in the chat
        # Approve from either surface → the other resolves automatically.
        # Only after approval does the pipeline proceed to the Healable Check.
        # -------------------------------------------------------------------
        Step(
            name="Notify Teams & Slack — Await HITL",
            agent=detective,
            description="""Post the RCAReport to Microsoft Teams (via Power Automate) and to Slack, then await Human Lead approval.

Input: RCAReport from the Analyze Failure step.

Your task:
1. Extract from the RCAReport: test_name, classification, confidence, root_cause,
   affected_file, suggested_fix, requires_human.
2. Call post_rca_to_teams with these values.
   - The call will pause for Human Lead confirmation (requires_confirmation=True).
   - The Adaptive Card will appear in the Teams channel AND in /approvals simultaneously.
   - Both surfaces reference the same approval record — approve from either one.
3. Call post_rca_to_slack with the same values.
   - This also pauses for confirmation via the same HITL mechanism.
4. After both confirmations are received, output a brief summary:
   "Teams and Slack notified. RCA for '<test_name>' approved by Human Lead. Proceeding to heal assessment."

Do NOT proceed to the Healable Check gate until both tools return successfully.""",
        ),
        Condition(
            name="Healable Check",
            evaluator=is_healable,
            # If healable: loop Medic up to 3× until verification_passes >= 3,
            # then validate with Healing Judge, then re-index the patched POM.
            steps=[
                Loop(
                    name="Verify Heal 3x",
                    steps=[Step(name="Patch and Verify", agent=medic)],
                    end_condition=healing_passed,
                    max_iterations=3,
                ),
                # -----------------------------------------------------------
                # Healing Judge — validates the patch is surgical (selector-only,
                # no logic changes) with confidence ≥ 0.99 before it is permanent.
                # -----------------------------------------------------------
                Step(
                    name="Validate Patch",
                    agent=healing_judge,
                    description="""As the Healing Judge, perform an adversarial review of the HealingPatch.

Input: HealingPatch from the Patch and Verify step.

DoD checklist:
- logic_changed must be False (REJECT immediately if True)
- diff must touch ONLY locator selector lines (no method signatures, assertions, or imports changed)
- verification_passes must be >= 3
- old_locator and new_locator must both be present and differ
- new_locator must use data-testid, role, or text strategy (no CSS/XPath)

Output: JudgeVerdict with confidence 0.0–1.0 and passed boolean.
confidence >= 0.99 → auto-approve → Librarian re-indexes.
confidence < 0.99  → reject patch with specific reasons → Medic must redo.""",
                ),
                # -----------------------------------------------------------
                # Librarian — re-indexes the patched POM so the KB stays current.
                # -----------------------------------------------------------
                Step(
                    name="Re-index Patched POM",
                    agent=librarian,
                    description="""As the Librarian, re-index the patched Page Object Model file.

Input: HealingPatch (contains file_path of the modified POM).

Your task:
1. Read the patched file from automation/pages/<file_path>.
2. Index it into the automation_kb vector store, replacing the old version.
3. Add a learning to qap_learnings_kb: record the old locator, new locator,
   and the pattern of failure so future agents can avoid the same issue.

Output: Confirmation that the file has been re-indexed.""",
                ),
            ],
            # Else: escalate to human — LOGIC_CHANGE or requires_human=True
            else_steps=[
                Step(
                    name="Flag for Human Review",
                    agent=detective,
                    description="The failure is not auto-healable (LOGIC_CHANGE or requires_human=True). Summarise the RCAReport and produce a human-readable escalation notice explaining why manual intervention is required.",
                ),
            ],
        ),
    ],
)
