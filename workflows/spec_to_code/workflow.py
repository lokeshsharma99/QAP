"""
Spec-to-Code Workflow
=====================

Workflow for converting Gherkin specifications to Playwright automation code.
End-to-end orchestration of spec → code → execute → triage → heal cycle.
"""

from agno.workflow import Workflow, Step

from agents.data_agent import data_agent
from agents.engineer import engineer
from agents.judge import judge
from teams.engineering import engineering_team

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
spec_to_code = Workflow(
    id="spec-to-code",
    name="Spec to Code",
    steps=[
        Step(
            name="Parse Feature File",
            agent=engineer,
            description="""As the Engineer, parse the Gherkin feature file to extract test scenarios.

Input: Path to .feature file provided in workflow input (e.g., automation/features/login.feature)

Your task:
1. Read and parse the .feature file
2. Extract all scenarios, steps, and examples
3. Identify page elements needed (buttons, forms, fields)
4. Create a structured representation of the feature

Output: Provide feature analysis with:
- Feature name and description
- List of scenarios with Given/When/Then steps
- Identified page elements and locators
- Data table examples if present

Focus on: Understanding the test flow and identifying all UI elements needed.""",
        ),
        Step(
            name="Provision Test Data",
            agent=data_agent,
            description="""As the Data Agent, generate test data with PII masking.

Input: Feature analysis from previous step including data table examples

Your task:
1. Analyze data requirements from feature file
2. Generate realistic test data for all fields
3. Apply PII masking to sensitive fields (email, phone, address)
4. Create run_context.json with test data configuration

Output: Provide run_context.json with:
- Test data values for all scenarios
- PII masking configuration
- Environment settings (base_url, browser, headless)
- Test execution parameters

Focus on: Generating valid, realistic test data while protecting PII.""",
        ),
        Step(
            name="Generate Page Objects",
            agent=engineer,
            description="""As the Engineer, generate modular Page Object Model classes.

Input: Feature analysis and run_context.json from previous steps

Your task:
1. Use Look-Before-You-Leap pattern to verify elements exist
2. Create Page Object classes for each page
3. Define locators using data-testid, role, or text strategies
4. Implement common methods (navigate, click, fill, getText)

Output: Generate Page Object files (e.g., pages/LoginPage.ts):
- Page class with element locators
- Action methods for each interaction
- Proper TypeScript typing
- No hardcoded locators or sleeps

Focus on: Creating reusable, maintainable Page Objects following BDD+POM best practices.""",
        ),
        Step(
            name="Generate Step Definitions",
            agent=data_agent,
            description="""As the Engineer, generate step definitions for test scenarios.

Input: Feature analysis, run_context.json, and Page Objects from previous steps

Your task:
1. Map Gherkin steps to Page Object methods
2. Generate step definition implementations
3. Use test data from run_context.json (no hardcoded values)
4. Implement proper error handling

Output: Generate step definition files (e.g., step_definitions/login.steps.ts):
- Step implementations for each Given/When/Then
- Integration with Page Objects
- Test data injection from run_context.json
- Proper TypeScript typing

Focus on: Creating reusable, data-driven step definitions with no hardcoded test data.""",
        ),
        Step(
            name="Code Quality Gate",
            agent=judge,
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

Focus on: Ensuring code meets quality standards before execution.""",
        ),
        Step(
            name="Local Verification",
            agent=engineer,
            description="""As the Engineer, run local containerized test execution.

Input: Generated code that passed quality gates

Your task:
1. Start Playwright in Docker container
2. Execute tests against AUT
3. Collect test results (pass/fail)
4. Capture screenshots on failure

Output: Provide test execution results with:
- Pass/fail status for each scenario
- Error messages if failures
- Screenshots of failures
- Execution time metrics

Focus on: Ensuring tests pass locally before creating PR.""",
        ),
        Step(
            name="Create Pull Request",
            agent=engineer,
            description="""As the Engineer, create GitHub branch and draft PR.

Input: Test execution results showing green run

Your task:
1. Create feature branch (e.g., feat/GDS-5-contact-info)
2. Commit generated code with conventional commit format
3. Push to GitHub
4. Create draft PR with description

Output: Provide PR details with:
- Branch name
- Commit hash
- PR URL
- Description of changes

Focus on: Proper Git workflow and PR process.""",
        ),
    ],
)
