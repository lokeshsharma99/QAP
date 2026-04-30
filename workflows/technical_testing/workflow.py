"""
Technical Testing Workflow
===========================

Workflow for using Playwright Test Agents (planner, generator, healer)
for rapid test generation and exploratory testing.
"""

from agno.workflow import Workflow, Step

from agents.technical_tester.agent import technical_tester
from workflows.technical_testing.instructions import INSTRUCTIONS

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
technical_testing = Workflow(
    id="technical-testing",
    name="Technical Testing",
    description="Generate rapid test suites using Playwright Test Agents for smoke testing, exploratory testing, and AUT validation",
    steps=[
        Step(
            name="Initialize Playwright Agents",
            agent=technical_tester,
            description="""Initialize Playwright Test Agents (planner, generator, healer) in the automation directory.

This step runs `npx playwright init-agents --loop=vscode` to generate the agent definitions.

Input: None

Output: Success message or error details

Focus on: Setting up the Playwright Test Agents infrastructure.
""",
        ),
        Step(
            name="Create Seed Test",
            agent=technical_tester,
            description="""Create a seed test file for Playwright Test Agents.

The seed test provides environment setup and context for the planner, generator, and healer agents.

Input: None

Output: Seed test file location

Focus on: Creating the foundational test that other agents will use as context.
""",
        ),
        Step(
            name="Generate Test Plan",
            agent=technical_tester,
            description="""Use the planner agent to generate a Markdown test plan.

Input: AUT URL and test requirements

Output: Markdown test plan in automation/technical-tests/specs/

Focus on: Exploring the AUT and generating a comprehensive test plan.
""",
        ),
        Step(
            name="Generate Playwright Tests",
            agent=technical_tester,
            description="""Use the generator agent to create Playwright tests from the Markdown plan.

Input: Markdown test plan file path

Output: Playwright test files in automation/technical-tests/tests/

Focus on: Transforming the plan into executable Playwright tests.
""",
        ),
        Step(
            name="Execute Tests",
            agent=technical_tester,
            description="""Run the generated Playwright tests.

Input: Optional specific test file, or run all tests

Output: Test execution results

Focus on: Validating the generated tests work correctly.
""",
        ),
        Step(
            name="Heal Failures",
            agent=technical_tester,
            description="""If tests failed, use the healer agent to repair them.

Input: Failing test file path

Output: Healed test file or error details

Focus on: Automatically repairing test failures through UI inspection and locator updates.
""",
        ),
    ],
)
