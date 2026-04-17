"""
Triage-Heal Workflow
====================

Workflow for converting test failures into automated healing.
End-to-end orchestration of failure → RCA → healing → verification cycle.
"""

from agno.workflow import OnError, Workflow, Step

from agents.detective import detective
from agents.engineer import engineer
from agents.healing_judge import healing_judge
from agents.librarian import librarian
from agents.medic import medic
from teams.operations import operations_team

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
triage_heal = Workflow(
    id="triage-heal",
    name="Triage and Heal",
    steps=[
        Step(
            name="Analyze Failure",
            agent=detective,
            description="""As the Detective, analyze trace.zip to identify root cause and generate RCAReport.

Input: Path to trace.zip file provided in workflow input

Your task:
1. Parse trace.zip to identify failure point
2. Analyze error messages and stack traces
3. Determine root cause (locator stale, logic error, data mismatch, environment failure)
4. Generate RCAReport with classification

Output: Provide RCAReport with:
- test_name
- failure_type (LOCATOR_STALE, LOGIC_ERROR, DATA_MISMATCH, ENVIRONMENT_FAILURE)
- root_cause description
- affected_locator (if applicable)
- suggested_locator (if LOCATOR_STALE)
- is_healable (boolean)
- confidence_score

Focus on: Accurate root cause analysis with proper classification.""",
        ),
        Step(
            name="Assess Healability",
            agent=detective,
            description="""As the Detective, determine if failure is healable.

Input: RCAReport from previous step

Your task:
1. Check if failure_type is LOCATOR_STALE
2. Verify confidence_score ≥80%
3. Confirm affected_locator and suggested_locator are present
4. Determine is_healable flag

Output: Provide healability assessment with:
- is_healable (boolean)
- reason if not healable
- confidence_score

Focus on: Only LOCATOR_STALE failures with high confidence are healable.""",
        ),
        Step(
            name="Generate Healing Patch",
            agent=medic,
            description="""As the Medic, create surgical edit if healable, otherwise escalate to human.

Input: RCAReport and healability assessment from previous steps

Your task:
1. If is_healable = True, generate HealingPatch with surgical edit
2. Calculate unified diff between old and new locator
3. Include justification from RCA
4. If not healable, escalate to human with RCA details

Output: Provide HealingPatch (if healable) or escalation message:
- file_path
- old_locator
- new_locator
- diff
- justification
- timestamp
- agent_id

Focus on: Surgical selector-only changes, no logic modifications.""",
        ),
        Step(
            name="Validate Healing Patch",
            agent=healing_judge,
            on_error=OnError.pause,
            description="""As the Healing Judge, validate patch is surgical (confidence ≥90%, no logic changes, proper locator strategy).

Input: HealingPatch from previous step

Your task:
1. Verify patch is selector-only (no logic changes)
2. Check confidence ≥90%
3. Validate proper locator strategy (data-testid, role, text)
4. Ensure no hardcoded test data
5. Approve or reject patch

Output: Provide validation verdict with:
- is_valid (boolean)
- confidence_score
- issues (list if invalid)
- approval (boolean)

Focus on: Ensuring patch is truly surgical and safe to apply.

Note: If validation fails (confidence < 90%), workflow will pause for human intervention. You can choose to retry (send back to Medic for rework) or skip (escalate to human).""",
        ),
        Step(
            name="Apply Healing Patch",
            agent=medic,
            description="""As the Medic, apply the healing patch to automation code.

Input: Approved HealingPatch from previous step

Your task:
1. Apply the surgical edit to the file
2. Verify the change was applied correctly
3. Prepare for verification run

Output: Confirm patch applied with:
- file_path modified
- lines_changed
- application_status

Focus on: Applying the patch accurately without side effects.""",
        ),
        Step(
            name="Verify Healing (3x)",
            agent=medic,
            description="""As the Medic, run test verification 3 times to confirm fix stability.

Input: Applied patch from previous step

Your task:
1. Re-run the failed test 3 times
2. Collect pass/fail results for each run
3. If all 3 pass, mark as successful
4. If any fail, rollback and escalate to human

Output: Provide verification results with:
- verification_results (list of 3 pass/fail)
- verification_passes (count)
- success (boolean)
- rollback_status (if failed)

Focus on: Stable fix that passes 3 consecutive runs.""",
        ),
        Step(
            name="Update Knowledge Base",
            agent=librarian,
            description="""As the Librarian, store healing learnings in knowledge base for future reference.

Input: RCAReport, HealingPatch, and verification results

Your task:
1. Store healing learnings in knowledge base
2. Index RCA patterns for future reference
3. Update site manifesto if locator patterns changed
4. Add metadata for traceability

Output: Confirm knowledge base updated with:
- Document count added
- Index status
- Traceability links

Focus on: Building knowledge for future healing and impact analysis.""",
        ),
    ],
)
