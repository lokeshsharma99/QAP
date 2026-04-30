"""
Full Regression Workflow
=========================

Workflow for end-to-end regression testing orchestration.
Full pipeline: spec → code → execute → triage → heal cycle.
"""

from agno.workflow import OnError, Workflow, Step

from agents.detective import detective
from agents.engineer import engineer
from agents.healing_judge import healing_judge
from agents.librarian import librarian
from agents.medic import medic

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
full_regression = Workflow(
    id="full-regression",
    name="Full Regression",
    description="Full regression: generate automation → execute tests → triage failures → heal locators",
    steps=[
        Step(
            name="Generate Automation",
            agent=engineer,
            description="""As the Engineer, generate automation code from requirements.

Input: RequirementContext or Jira ticket ID provided in workflow input

Your task:
1. Parse requirements and acceptance criteria
2. Generate Page Objects using Look-Before-You-Leap
3. Generate step definitions with data injection
4. Ensure proper locator strategies (data-testid, role, text)

Output: Provide generated automation code with:
- Page Object files
- Step definition files
- run_context.json with test data
- Feature file if generated from requirements

Focus on: Generating high-quality automation following BDD+POM best practices.""",
        ),
        Step(
            name="Execute Tests",
            agent=engineer,
            description="""As the Engineer, run generated tests and collect results.

Input: Generated automation code from previous step

Your task:
1. Start Playwright in Docker container
2. Execute all test scenarios
3. Collect pass/fail results
4. Capture screenshots and traces for failures

Output: Provide test execution results with:
- Pass/fail status for each scenario
- Error messages for failures
- Screenshots of failures
- trace.zip for failed tests

Focus on: Comprehensive test execution with detailed failure information.""",
        ),
        Step(
            name="Analyze Failures",
            agent=detective,
            description="""As the Detective, analyze test failures and generate RCA reports.

Input: Test execution results with trace.zip for failures

Your task:
1. Parse trace.zip to identify failure point
2. Analyze error messages and stack traces
3. Determine root cause (locator stale, logic error, data mismatch, etc.)
4. Generate RCAReport with classification

Output: Provide RCAReport for each failure with:
- test_name
- failure_type (LOCATOR_STALE, LOGIC_ERROR, DATA_MISMATCH, ENVIRONMENT_FAILURE)
- root_cause description
- affected_locator (if applicable)
- suggested_locator (if LOCATOR_STALE)
- is_healable (boolean)
- confidence_score

Focus on: Accurate root cause analysis with high confidence classification.""",
        ),
        Step(
            name="Generate Healing Patch",
            agent=medic,
            description="""As the Medic, create surgical edit if healable.

Input: RCAReport from previous step

Your task:
1. Check if failure is healable (LOCATOR_STALE with confidence ≥80%)
2. Generate HealingPatch with surgical edit
3. Calculate unified diff
4. Include justification from RCA

Output: Provide HealingPatch with:
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
            description="""As the Healing Judge, validate patch is surgical.

Input: HealingPatch from previous step

Your task:
1. Verify patch is selector-only (no logic changes)
2. Check confidence ≥90%
3. Validate proper locator strategy (data-testid, role, text)
4. Ensure no hardcoded test data

Output: Provide validation verdict with:
- is_valid (boolean)
- confidence_score
- issues (list if invalid)
- approval (boolean)

Focus on: Ensuring patch is truly surgical and safe to apply.

Note: If validation fails (confidence < 90%), workflow will pause for human intervention. You can choose to retry (send back to Medic for rework) or skip (escalate to human).""",
        ),
        Step(
            name="Verify Healing",
            agent=medic,
            description="""As the Medic, verify tests pass after healing.

Input: Approved HealingPatch from previous step

Your task:
1. Apply the healing patch to the file
2. Re-run the failed test 3 times
3. Collect verification results
4. Rollback if verification fails

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
            description="""As the Librarian, update knowledge base with new learnings.

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
