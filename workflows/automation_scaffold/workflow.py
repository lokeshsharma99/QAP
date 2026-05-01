"""
Automation Scaffold Workflow
============================

Workflow for scaffolding BDD+POM automation framework when a new project is initiated.
"""

from agno.workflow import Workflow, Step
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
    ],
)
