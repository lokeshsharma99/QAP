"""
Full Lifecycle Workflow
========================

End-to-end workflow from requirement to execution/report using individual agents.
Coordinates all agents: Architect, Scribe, Discovery, Librarian, Engineer, Data Agent, Detective, Medic, Judge.
"""

from agno.workflow import OnError, Workflow, Step

from agents.architect import architect
from agents.data_agent import data_agent
from agents.detective import detective
from agents.discovery import discovery
from agents.engineer import engineer
from agents.healing_judge import healing_judge
from agents.judge import judge
from agents.librarian import librarian
from agents.medic import medic
from agents.scribe import scribe

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
full_lifecycle = Workflow(
    id="full-lifecycle",
    name="Full STLC Pipeline",
    description="End-to-end: requirement → spec → code → verify → PR using all 9 agents",
    steps=[
        Step(
            name="Requirement Analysis",
            agent=architect,
            description="""As the Architect, analyze requirements and generate RequirementContext.

Input: Jira ticket ID or requirement description provided in workflow input

Your task:
1. Fetch Jira ticket details if a ticket ID is provided
2. Analyze requirements and extract acceptance criteria
3. Identify affected Page Objects by querying knowledge base
4. Generate RequirementContext with execution plan

Output: Provide RequirementContext with:
- ticket_id, title, description
- acceptance_criteria (list)
- affected_page_objects (list)
- execution_plan
- priority, estimated_complexity

Focus on: Producing high-quality RequirementContext with clear acceptance criteria.""",
        ),
        Step(
            name="Gherkin Generation",
            agent=scribe,
            description="""As the Scribe, convert RequirementContext to Gherkin specification.

Input: RequirementContext from previous step

Your task:
1. Convert acceptance criteria to Gherkin scenarios
2. Create Given/When/Then steps with proper structure
3. Identify data requirements for test scenarios
4. Generate GherkinSpec with reusable steps

Output: Provide GherkinSpec with:
- feature_name, feature_description
- scenarios (list with Given/When/Then steps)
- data_requirements (list)
- traceability (ticket_id, requirement_context_id)
- file_path (target .feature file path)

Focus on: Producing high-quality Gherkin spec with clear scenarios and proper data requirements.""",
        ),
        Step(
            name="Quality Gate - Spec",
            agent=judge,
            on_error=OnError.pause,
            description="""As the Judge, validate GherkinSpec against DoD checklist.

Input: GherkinSpec from previous step

Your task:
1. Review GherkinSpec for syntax errors
2. Check step reusability
3. Verify data requirements are complete
4. Validate traceability to source ticket
5. Provide JudgeVerdict with confidence score

Output: Provide JudgeVerdict with:
- confidence (0-100, auto-approve at ≥90)
- passed (boolean)
- checklist_results (list)
- feedback (if rejected)

Focus on: Ensuring spec quality before proceeding to automation generation.

Note: If quality gate fails (confidence < 90%), workflow will pause for human intervention. You can choose to retry (send back to Scribe for rework) or skip (escalate to human).""",
        ),
        Step(
            name="Context Discovery",
            agent=discovery,
            description="""As the Discovery Agent, crawl AUT and generate Site Manifesto.

Input: AUT URL from workflow input or from GherkinSpec metadata

Your task:
1. Crawl AUT to extract UI elements and page structure
2. Identify interactive components (buttons, forms, fields)
3. Determine optimal locator strategies (data-testid, role, text)
4. Generate SiteManifesto with comprehensive coverage

Output: Provide SiteManifesto with:
- aut_base_url, aut_name
- pages (list with components, locators)
- total_pages, total_components
- high_risk_actions (list)

Focus on: Comprehensive AUT coverage for Look-Before-You-Leap verification.""",
        ),
        Step(
            name="Index Knowledge Base",
            agent=librarian,
            description="""As the Librarian, index SiteManifesto and codebase into knowledge base.

Input: SiteManifesto from previous step

Your task:
1. Index SiteManifesto with hybrid search (vector + keyword)
2. Index codebase Page Objects and Step Definitions
3. Verify knowledge base is searchable
4. Add metadata for traceability

Output: Confirm knowledge base updated with:
- Document count added
- Index status
- Searchability verification

Focus on: Building searchable knowledge base for semantic queries.""",
        ),
        Step(
            name="Test Data Provisioning",
            agent=data_agent,
            description="""As the Data Agent, generate test data with PII masking.

Input: GherkinSpec data requirements from previous step

Your task:
1. Analyze data requirements from GherkinSpec
2. Generate realistic test data for all fields
3. Apply PII masking to sensitive fields (email, phone, address, NINO)
4. Create RunContext with test data configuration

Output: Provide RunContext with:
- test_user (credentials with PII masked)
- db_seed_queries (SQL for test data setup)
- api_mocks (endpoint mocks if needed)
- cleanup_queries (SQL for cleanup)
- environment, base_url, browser_config

Focus on: Generating valid, realistic test data while protecting PII.""",
        ),
        Step(
            name="Page Object Generation",
            agent=engineer,
            description="""As the Engineer, generate Page Object Model classes.

Input: GherkinSpec, SiteManifesto, and RunContext from previous steps

Your task:
1. Use Look-Before-You-Leap pattern with SiteManifesto to verify elements
2. Create Page Object classes for each page
3. Define locators using data-testid, role, or text strategies
4. Implement common methods (navigate, click, fill, getText, waitForVisible)

Output: Generate Page Object files (e.g., pages/LoginPage.ts):
- Page class with element locators
- Action methods for each interaction
- Proper TypeScript typing
- No hardcoded locators or sleeps

Focus on: Creating reusable, maintainable Page Objects following BDD+POM best practices.""",
        ),
        Step(
            name="Step Definition Generation",
            agent=engineer,
            description="""As the Engineer, generate step definitions for test scenarios.

Input: GherkinSpec, RunContext, and Page Objects from previous steps

Your task:
1. Map Gherkin steps to Page Object methods
2. Generate step definition implementations
3. Use test data from RunContext (no hardcoded values)
4. Implement proper error handling

Output: Generate step definition files (e.g., step_definitions/login.steps.ts):
- Step implementations for each Given/When/Then
- Integration with Page Objects
- Test data injection from RunContext
- Proper TypeScript typing

Focus on: Creating reusable, data-driven step definitions with no hardcoded test data.""",
        ),
        Step(
            name="Code Quality Gate",
            agent=judge,
            on_error=OnError.pause,
            description="""As the Judge, validate generated code quality.

Input: Generated Page Objects and step definitions from previous steps

Your task:
1. Run eslint on all generated files
2. Run TypeScript type-check
3. Verify no hardcoded sleeps or waitForTimeout
4. Check locator strategies (data-testid, role, text)
5. Validate no hardcoded test data

Output: Provide quality gate verdict with:
- eslint pass/fail status
- type-check pass/fail status
- List of any violations (sleeps, hardcoded data, bad locators)
- Overall pass/fail recommendation

Focus on: Ensuring code meets quality standards before execution.

Note: If quality gate fails (confidence < 90%), workflow will pause for human intervention. You can choose to retry (send back to Engineer for rework) or skip (escalate to human).""",
        ),
        Step(
            name="Test Execution",
            agent=engineer,
            description="""As the Engineer, execute tests and collect results.

Input: Generated code that passed quality gates

Your task:
1. Start Playwright in Docker container
2. Execute all test scenarios
3. Collect pass/fail results and capture traces for failures
4. Generate ExecutionResult with detailed results

Output: Provide ExecutionResult with:
- run_id, timestamp
- total_scenarios, passed, failed, skipped
- test_results (list of TestResult with scenario_name, status, duration_ms, error_message, screenshot_path, trace_path)
- has_failures flag
- failure_summary

Focus on: Comprehensive test execution with detailed failure information for triage.""",
        ),
        Step(
            name="Failure Analysis",
            agent=detective,
            description="""As the Detective, analyze test failures and determine root cause.

Input: ExecutionResult with failures (if has_failures = True)

Your task:
1. Parse trace.zip files for failed tests
2. Analyze error messages and stack traces
3. Determine root cause (LOCATOR_STALE, LOGIC_ERROR, DATA_MISMATCH, ENV_FAILURE)
4. Generate RCAReport with classification and confidence

Output: Provide RCAReport with:
- test_name, failure_type, confidence
- root_cause description
- affected_locator (if LOCATOR_STALE)
- is_healable (boolean)
- recommendations

Focus on: Accurate root cause analysis with proper classification.""",
        ),
        Step(
            name="Healing Patch Generation",
            agent=medic,
            description="""As the Medic, generate surgical healing patch if healable.

Input: RCAReport with is_healable = True

Your task:
1. If is_healable, generate HealingPatch with surgical edit
2. Calculate unified diff between old and new locator
3. Include justification from RCA
4. If not healable, escalate to human with RCA details

Output: Provide HealingPatch (if healable) with:
- old_locator, new_locator
- file_path, page_name, line_number
- diff, justification
- verification_passes (0 initially)

Focus on: Surgical selector-only changes, no logic modifications.""",
        ),
        Step(
            name="Healing Patch Validation",
            agent=healing_judge,
            on_error=OnError.pause,
            description="""As the Healing Judge, validate patch is surgical and safe.

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
            name="Apply and Verify Healing",
            agent=medic,
            description="""As the Medic, apply patch and verify 3x runs.

Input: Approved HealingPatch from previous step

Your task:
1. Apply the surgical edit to the file
2. Verify the change was applied correctly
3. Re-run the failed test 3 times
4. Collect pass/fail results for each run

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
            description="""As the Librarian, store healing learnings in knowledge base.

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
        Step(
            name="Final Quality Gate",
            agent=judge,
            on_error=OnError.pause,
            description="""As the Judge, perform final quality gate review.

Input: All previous outputs and results

Your task:
1. Review entire workflow execution
2. Validate all phases completed successfully
3. Check final test execution results
4. Provide JudgeVerdict with overall confidence and approval

Output: Provide JudgeVerdict with:
- confidence (0-100, auto-approve at ≥90)
- passed (boolean)
- checklist_results (list)
- feedback (if rejected)

Focus on: Ensuring end-to-end quality before marking workflow complete.

Note: If quality gate fails (confidence < 90%), workflow will pause for human intervention. You can choose to retry (review again) or skip (escalate to human).""",
        ),
        Step(
            name="Report Generation",
            agent=scribe,
            description="""As the Scribe, generate final execution report.

Input: All contracts and results from workflow execution

Your task:
1. Compile all hand-offs and results
2. Generate comprehensive report with:
   - Requirement analysis summary
   - AUT discovery summary
   - Automation generation summary
   - Test execution results
   - Failure analysis and healing (if applicable)
   - Quality gate verdict
3. Format report for stakeholder review

Output: Provide FinalReport with:
- workflow_id, run_id, timestamp
- overall_status (success, partial_success, failed)
- summary of each phase
- ExecutionResult
- RCAReport (if failures)
- HealingPatch (if healing applied)
- JudgeVerdict
- recommendations

Focus on: Clear, comprehensive report for stakeholder visibility.""",
        ),
    ],
)
