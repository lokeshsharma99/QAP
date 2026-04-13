"""
Full Lifecycle Workflow
========================

End-to-end workflow from requirement to execution/report using teams.
Coordinates all squads: Strategy, Context, Engineering, Operations.
"""

from agno.workflow import Workflow, Step

from teams.context import context_team
from teams.engineering import engineering_team
from teams.operations import operations_team
from teams.strategy import strategy_team

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
full_lifecycle = Workflow(
    id="full-lifecycle",
    name="Full Lifecycle",
    steps=[
        Step(
            name="Requirement Analysis",
            agent=strategy_team,
            description="""As the Strategy Team (Architect + Scribe), analyze requirements and generate specifications.

Input: Jira ticket ID or requirement description provided in workflow input

Your task:
1. Architect: Fetch Jira ticket, analyze requirements, extract acceptance criteria, generate RequirementContext
2. Scribe: Convert RequirementContext to GherkinSpec with scenarios and data requirements
3. Judge: Review GherkinSpec against DoD checklist (confidence ≥90% to proceed)

Output: Provide SquadHandoff with:
- from_squad: strategy
- to_squad: engineering
- contract_type: GherkinSpec
- contract_data: Serialized GherkinSpec with feature_name, scenarios, data_requirements

Focus on: Producing high-quality Gherkin spec with clear scenarios and proper data requirements.""",
        ),
        Step(
            name="Context Discovery",
            agent=context_team,
            description="""As the Context Team (Discovery + Librarian), build AUT knowledge base.

Input: AUT URL from workflow input or from GherkinSpec metadata

Your task:
1. Discovery: Crawl AUT to extract UI elements, generate SiteManifesto
2. Librarian: Index SiteManifesto and codebase into knowledge base with hybrid search
3. Verify: Confirm knowledge base is searchable and contains relevant information

Output: Provide SquadHandoff with:
- from_squad: context
- to_squad: engineering
- contract_type: SiteManifesto
- contract_data: Serialized SiteManifesto with pages and components

Focus on: Comprehensive AUT coverage and searchable knowledge base for semantic queries.""",
        ),
        Step(
            name="Automation Generation",
            agent=engineering_team,
            description="""As the Engineering Team (Engineer + Data Agent), generate automation code.

Input: SquadHandoff from Strategy Team (GherkinSpec) and Context Team (SiteManifesto)

Your task:
1. Data Agent: Generate RunContext with test data and PII masking
2. Engineer: Generate Page Objects using Look-Before-You-Leap with SiteManifesto
3. Engineer: Generate step definitions with data injection from RunContext
4. Judge: Validate generated code (eslint, type-check, no hardcoded sleeps)

Output: Provide SquadHandoff with:
- from_squad: engineering
- to_squad: operations
- contract_type: RunContext + AutomationCode
- contract_data: Serialized RunContext and generated code paths

Focus on: High-quality automation following BDD+POM best practices with proper locators.""",
        ),
        Step(
            name="Test Execution",
            agent=engineering_team,
            description="""As the Engineering Team, execute tests and collect results.

Input: Generated automation code from previous step

Your task:
1. Engineer: Start Playwright in Docker container
2. Engineer: Execute all test scenarios
3. Engineer: Collect pass/fail results and capture traces for failures
4. Engineer: Generate ExecutionResult with detailed results

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
            agent=operations_team,
            description="""As the Operations Team (Detective + Medic), analyze failures and heal if possible.

Input: ExecutionResult with failures (if has_failures = True)

Your task:
1. Detective: Parse trace.zip, analyze error messages, determine root cause
2. Detective: Generate RCAReport with classification (LOCATOR_STALE, LOGIC_ERROR, etc.)
3. Detective: Assess healability (LOCATOR_STALE with confidence ≥80%)
4. Medic: If healable, generate HealingPatch with surgical edit
5. Healing Judge: Validate patch is surgical (confidence ≥90%, selector-only)
6. Medic: Apply patch and verify 3x runs

Output: Provide SquadHandoff with:
- from_squad: operations
- to_squad: strategy
- contract_type: RCAReport + HealingPatch (if applicable)
- contract_data: Serialized RCAReport and HealingPatch

Focus on: Accurate RCA and surgical healing only for LOCATOR_STALE failures.""",
        ),
        Step(
            name="Quality Gate",
            agent=strategy_team,
            description="""As the Strategy Team with Judge, perform final quality gate review.

Input: All previous hand-offs and results

Your task:
1. Judge: Review entire workflow execution
2. Judge: Validate all contracts were properly passed
3. Judge: Check final test execution results
4. Judge: Provide JudgeVerdict with overall confidence and approval

Output: Provide JudgeVerdict with:
- confidence (0-100, auto-approve at ≥90)
- passed (boolean)
- checklist_results (list of ChecklistResult)
- feedback (detailed feedback if rejected)

Focus on: Ensuring end-to-end quality before marking workflow complete.""",
        ),
        Step(
            name="Report Generation",
            agent=strategy_team,
            description="""As the Strategy Team, generate final execution report.

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
