"""
Automation Scaffold Workflow
============================

Workflow for scaffolding BDD+POM automation framework when a new project is initiated.
"""

from agno.workflow import Workflow, Step
from agents.data_agent import data_agent
from agents.engineer import engineer
from contracts.automation_scaffold import AutomationScaffold

# ---------------------------------------------------------------------------
# Create Workflow
# ---------------------------------------------------------------------------
automation_scaffold = Workflow(
    id="automation-scaffold",
    name="New Project Scaffold",
    description="Scaffold a complete BDD+POM automation framework for a new project",
    steps=[
        Step(
            name="Create Scaffold Structure",
            agent=engineer,
            description="""As the Engineer, scaffold a complete BDD+POM automation framework.

Input: ScaffoldConfig provided in workflow input with:
- project_name: Name of the automation project
- base_url: Base URL of the application under test
- output_dir: Directory where scaffold will be created (default: automation)
- browser: Browser to use (default: chromium)
- headless: Whether to run in headless mode (default: true)

Your task:
1. Create directory structure (features/, step_definitions/, pages/, config/, tests/, reports/, hooks/)
2. Create configuration files (package.json, playwright.config.ts, cucumber.conf.ts, tsconfig.json)
3. Create BasePage class with common methods (navigate, click, fill, getText, waitForVisible, isVisible, screenshot)
4. Create example files (example.feature, example.steps.ts, HomePage.ts)

Output: Provide AutomationScaffold with:
- project_name
- config (ScaffoldConfig)
- structure (ScaffoldStructure)
- files (list of ScaffoldFile)
- success (boolean)
- message (status message)
- created_at (timestamp)

Focus on: Following AGENTS.md coding conventions, using absolute imports, including section headers with 75-char # --- format, ensuring proper formatting, creating modular reusable code, following BDD+POM best practices.""",
        ),
        Step(
            name="Provision Initial Test Fixtures",
            agent=data_agent,
            description="""As the Data Agent, create the initial test data fixtures for the scaffolded automation framework.

Input: The AutomationScaffold produced in the previous step (project_name, base_url).

Your task:
1. Create automation/fixtures/test-users.json — a set of synthetic test users (admin, standard user, guest)
   covering the main roles the AUT is likely to have. Use faker-style data: no real PII.
2. Create automation/fixtures/test-data.json — common test data constants (IDs, names, amounts)
   that the step definitions will need at runtime.
3. Create automation/data/env-config.ts — exports BASE_URL, HEADLESS, BROWSER from environment
   variables with sensible defaults for local and CI.
4. Ensure all generated data:
   - Uses unique constraints (UUIDs for IDs, unique emails per user)
   - Is PII-masked (no real names, emails, phones)
   - Has a cleanup_ids list so tests can tear down created records

Output: Confirm which fixture files were created and their paths.

Critical rules:
- NEVER use real email addresses, real names, or production data.
- All passwords must be strong random strings, NOT 'password123' or similar.""",
        ),    ],
)