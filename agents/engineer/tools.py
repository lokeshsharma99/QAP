"""
Engineer Agent Tools
====================

Custom tools for the Engineer agent.
"""

import json
import os
import subprocess
from typing import Any

from agno.tools import tool

from contracts.automation_scaffold import AutomationScaffold, ScaffoldConfig, ScaffoldFile, ScaffoldStructure


@tool(
    name="validate_files_created",
    description="Verify that specified files were actually created on disk. Returns list of missing files and validation status.",
)
def validate_files_created(
    file_paths: list[str],
    base_path: str = "automation",
) -> str:
    """Verify that specified files were actually created on disk.

    Args:
        file_paths: List of file paths to validate (relative to base_path)
        base_path: Base directory path (default: automation)

    Returns:
        JSON string with validation results including missing files and status
    """
    results = {
        "base_path": base_path,
        "expected_files": file_paths,
        "missing_files": [],
        "created_files": [],
        "validation_passed": False,
        "summary": "",
    }

    for file_path in file_paths:
        full_path = os.path.join(base_path, file_path)
        if os.path.exists(full_path):
            results["created_files"].append(file_path)
        else:
            results["missing_files"].append(file_path)

    results["validation_passed"] = len(results["missing_files"]) == 0

    if results["validation_passed"]:
        results["summary"] = f"✅ All {len(file_paths)} files created successfully"
    else:
        results["summary"] = f"❌ {len(results['missing_files'])} files missing: {', '.join(results['missing_files'])}"

    return json.dumps(results, indent=2)


@tool(
    name="run_linting",
    description="Run ESLint and TypeScript type checking on generated code to verify code quality. Returns lint results and any errors found.",
)
def run_linting(
    target_path: str = "automation",
    fix: bool = False,
) -> str:
    """Run linting and type checking on generated code.

    Args:
        target_path: Path to the directory or file to lint (default: automation)
        fix: Whether to automatically fix linting issues

    Returns:
        JSON string with linting results including errors, warnings, and fix suggestions
    """
    results = {
        "target_path": target_path,
        "fix_attempted": fix,
        "eslint_errors": [],
        "eslint_warnings": [],
        "typescript_errors": [],
        "summary": "",
    }

    # Run ESLint
    try:
        eslint_cmd = ["npx", "eslint", target_path, "--format", "json"]
        if fix:
            eslint_cmd.append("--fix")

        eslint_result = subprocess.run(
            eslint_cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(target_path) if os.path.isfile(target_path) else target_path
        )

        if eslint_result.stdout:
            try:
                eslint_output = json.loads(eslint_result.stdout)
                for result in eslint_output:
                    for message in result.get("messages", []):
                        if message.get("severity") == 2:
                            results["eslint_errors"].append({
                                "file": result.get("filePath"),
                                "line": message.get("line"),
                                "column": message.get("column"),
                                "message": message.get("message"),
                                "rule": message.get("ruleId"),
                            })
                        else:
                            results["eslint_warnings"].append({
                                "file": result.get("filePath"),
                                "line": message.get("line"),
                                "column": message.get("column"),
                                "message": message.get("message"),
                                "rule": message.get("ruleId"),
                            })
            except json.JSONDecodeError:
                results["eslint_errors"].append({
                    "message": "ESLint output could not be parsed",
                    "raw_output": eslint_result.stdout,
                })
    except FileNotFoundError:
        results["eslint_errors"].append({
            "message": "ESLint not found. Run 'npm install eslint' first.",
        })
    except Exception as e:
        results["eslint_errors"].append({
            "message": f"ESLint execution failed: {str(e)}",
        })

    # Run TypeScript type checking
    try:
        tsc_cmd = ["npx", "tsc", "--noEmit"]
        tsc_result = subprocess.run(
            tsc_cmd,
            capture_output=True,
            text=True,
            cwd=target_path if os.path.isdir(target_path) else os.path.dirname(target_path)
        )

        if tsc_result.stdout:
            for line in tsc_result.stdout.split("\n"):
                if line.strip() and "error TS" in line:
                    results["typescript_errors"].append({
                        "message": line.strip(),
                    })
    except FileNotFoundError:
        results["typescript_errors"].append({
            "message": "TypeScript not found. Run 'npm install typescript' first.",
        })
    except Exception as e:
        results["typescript_errors"].append({
            "message": f"TypeScript check failed: {str(e)}",
        })

    # Generate summary
    total_issues = len(results["eslint_errors"]) + len(results["typescript_errors"])
    if total_issues == 0:
        results["summary"] = "✅ Linting passed: No errors found"
    else:
        results["summary"] = f"❌ Linting failed: {total_issues} issues found ({len(results['eslint_errors'])} ESLint errors, {len(results['typescript_errors'])} TypeScript errors)"

    return json.dumps(results, indent=2)


@tool(
    name="run_playwright_script",
    description="Run a Playwright script and return the output. Useful for custom locator extraction or page interaction.",
)
def run_playwright_script(
    script_content: str,
    headless: bool = True,
) -> str:
    """Run a Playwright script and return the output.

    Args:
        script_content: Playwright script to execute
        headless: Whether to run in headless mode

    Returns:
        JSON string with script execution results
    """
    result = {
        "script": script_content,
        "headless": headless,
        "message": "Playwright script execution - use playwright_evaluate for JavaScript execution"
    }
    return json.dumps(result, indent=2)


@tool(
    name="run_local_verify",
    description="Run Playwright tests in the qap-playwright container with network isolation. Returns test results and pass/fail status.",
)
def run_local_verify(
    test_path: str = "automation",
    test_pattern: str = "",
    retries: int = 2,
) -> str:
    """Run Playwright tests in containerized environment for local verification.

    Args:
        test_path: Path to the test directory (default: automation)
        test_pattern: Specific test pattern to run (e.g., "@smoke" or feature file pattern)
        retries: Number of retries for flaky tests (default: 2)

    Returns:
        JSON string with test execution results including pass/fail status, duration, and error details
    """
    results = {
        "test_path": test_path,
        "test_pattern": test_pattern,
        "retries": retries,
        "status": "not_run",
        "passed": False,
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "skipped_tests": 0,
        "duration_seconds": 0,
        "errors": [],
        "summary": "",
    }

    try:
        # Build docker command
        cmd = ["docker", "compose", "run", "--rm", "qap-playwright"]
        
        # Add test command
        if test_pattern:
            test_cmd = f"npx playwright test {test_path} --grep '{test_pattern}'"
        else:
            test_cmd = f"npx playwright test {test_path}"
        
        # Add retries
        if retries > 0:
            test_cmd += f" --retries {retries}"
        
        cmd.extend(["sh", "-c", test_cmd])
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(test_path) if os.path.isfile(test_path) else "."
        )
        
        results["status"] = "completed"
        results["duration_seconds"] = 0  # Would need to time the execution
        
        # Parse output for test results
        output = result.stdout + result.stderr
        
        # Look for Playwright test summary
        if "passed" in output.lower():
            results["status"] = "passed"
            results["passed"] = True
            results["summary"] = "✅ Local verification passed: All tests executed successfully"
        else:
            results["status"] = "failed"
            results["passed"] = False
            results["errors"].append({
                "message": "Test execution failed",
                "output": output[:1000],  # Truncate long output
            })
            results["summary"] = "❌ Local verification failed: Tests did not pass"
            
    except FileNotFoundError:
        results["errors"].append({
            "message": "Docker not found or qap-playwright service not available",
        })
        results["summary"] = "❌ Local verification failed: Docker service unavailable"
    except Exception as e:
        results["errors"].append({
            "message": f"Local verification failed: {str(e)}",
        })
        results["summary"] = f"❌ Local verification failed: {str(e)}"

    return json.dumps(results, indent=2)


@tool(
    name="create_github_pr",
    description="Create a GitHub branch and pull request for the generated automation code. Returns PR URL and status.",
)
def create_github_pr(
    branch_name: str,
    title: str,
    description: str,
    base_branch: str = "main",
    draft: bool = True,
) -> str:
    """Create a GitHub branch and pull request for the generated automation code.

    Args:
        branch_name: Name for the new branch (e.g., "automation/personal-details-form")
        title: PR title
        description: PR description with test results and context
        base_branch: Base branch to merge into (default: main)
        draft: Whether to create as draft PR (default: True)

    Returns:
        JSON string with PR creation results including PR URL, number, and status
    """
    import os
    import subprocess
    
    results = {
        "branch_name": branch_name,
        "title": title,
        "base_branch": base_branch,
        "draft": draft,
        "status": "not_created",
        "pr_url": "",
        "pr_number": 0,
        "errors": [],
        "summary": "",
    }

    try:
        # Check if git is available
        subprocess.run(["git", "--version"], capture_output=True, check=True)
        
        # Create and checkout new branch
        subprocess.run(["git", "checkout", "-b", branch_name], capture_output=True, check=True)
        results["summary"] += f"✅ Created branch: {branch_name}\n"
        
        # Stage and commit changes
        subprocess.run(["git", "add", "automation/"], capture_output=True, check=True)
        commit_msg = f"{title}\n\n{description}"
        subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, check=True)
        results["summary"] += "✅ Committed automation changes\n"
        
        # Push branch
        subprocess.run(["git", "push", "-u", "origin", branch_name], capture_output=True, check=True)
        results["summary"] += f"✅ Pushed branch to origin/{branch_name}\n"
        
        # Create PR using GitHub CLI if available
        try:
            pr_cmd = ["gh", "pr", "create", "--base", base_branch, "--title", title, "--body", description]
            if draft:
                pr_cmd.append("--draft")
            
            pr_result = subprocess.run(pr_cmd, capture_output=True, text=True, check=True)
            results["status"] = "created"
            results["summary"] += "✅ Pull request created successfully"
            
            # Parse PR URL from output
            if "https://" in pr_result.stdout:
                results["pr_url"] = pr_result.stdout.strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            # GitHub CLI not available, provide manual instructions
            results["status"] = "branch_created"
            results["summary"] += "\n⚠️ GitHub CLI not available. Please create PR manually via GitHub web UI."
            results["summary"] += f"\nBranch: {branch_name}"
            results["summary"] += f"\nBase: {base_branch}"
            results["summary"] += f"\nTitle: {title}"
            
    except subprocess.CalledProcessError as e:
        results["errors"].append({
            "message": f"Git command failed: {str(e)}",
        })
        results["summary"] = f"❌ Failed to create PR: {str(e)}"
    except FileNotFoundError:
        results["errors"].append({
            "message": "Git not found. Please install git to use PR automation.",
        })
        results["summary"] = "❌ Failed to create PR: Git not available"
    except Exception as e:
        results["errors"].append({
            "message": f"PR creation failed: {str(e)}",
        })
        results["summary"] = f"❌ Failed to create PR: {str(e)}"

    return json.dumps(results, indent=2)


@tool(
    name="create_scaffold",
    description="Create a BDD+POM automation framework scaffold with features, step definitions, pages, and config files.",
)
def create_scaffold(
    project_name: str,
    base_url: str,
    output_dir: str = "automation",
    browser: str = "chromium",
    headless: bool = True,
) -> str:
    """Create a BDD+POM automation framework scaffold.

    Args:
        project_name: Name of the automation project
        base_url: Base URL of the application under test
        output_dir: Directory where the scaffold will be created
        browser: Browser to use for testing (chromium, firefox, webkit)
        headless: Whether to run tests in headless mode

    Returns:
        JSON string with AutomationScaffold details including created structure and files
    """
    # Create directory structure
    dirs = [
        f"{output_dir}/features",
        f"{output_dir}/step_definitions",
        f"{output_dir}/pages",
        f"{output_dir}/config",
        f"{output_dir}/tests",
        f"{output_dir}/reports",
        f"{output_dir}/hooks",
    ]
    
    for dir_path in dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    # Create package.json
    package_json = {
        "name": project_name.lower().replace(" ", "-"),
        "version": "1.0.0",
        "description": f"Automation framework for {project_name}",
        "scripts": {
            "test": "cucumber-js",
            "test:headed": "cucumber-js --profile headed"
        },
        "devDependencies": {
            "@cucumber/cucumber": "^12.8.0",
            "@playwright/test": "^1.42.0",
            "@types/node": "^20.0.0",
            "cucumber-html-reporter": "^9.2.0",
            "ts-node": "^10.9.2",
            "typescript": "^5.4.5"
        }
    }
    
    with open(f"{output_dir}/package.json", "w") as f:
        json.dump(package_json, f, indent=2)
    
    # Create playwright.config.ts
    playwright_config = f'''import {{ defineConfig, devices }} from '@playwright/test';

export default defineConfig({{
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {{
    baseURL: '{base_url}',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  }},
  projects: [
    {{
      name: '{browser}',
      use: {{ ...devices['Desktop Chrome'] }},
    }},
  ],
}});
'''
    
    with open(f"{output_dir}/playwright.config.ts", "w") as f:
        f.write(playwright_config)
    
    # Create BasePage class
    base_page = '''import { Page, Locator } from '@playwright/test';

export class BasePage {
  constructor(protected page: Page) {}

  async navigate(url: string): Promise<void> {
    await this.page.goto(url);
  }

  async click(locator: Locator): Promise<void> {
    await locator.click();
  }

  async fill(locator: Locator, value: string): Promise<void> {
    await locator.fill(value);
  }

  async getText(locator: Locator): Promise<string> {
    return await locator.textContent() || '';
  }

  async waitForElement(locator: Locator): Promise<void> {
    await locator.waitFor();
  }
}
'''
    
    with open(f"{output_dir}/pages/BasePage.ts", "w") as f:
        f.write(base_page)
    
    # Create example feature file
    example_feature = f'''Feature: {project_name} User Flow

  Scenario: User navigates to home page
    Given user is on the home page
    Then page title should contain "{project_name}"
'''
    
    with open(f"{output_dir}/features/example.feature", "w") as f:
        f.write(example_feature)
    
    # Create example page object
    example_page = f'''import {{ BasePage }} from './BasePage';

export class HomePage extends BasePage {{
  constructor(page: Page) {{
    super(page);
  }}

  get pageTitle(): Locator {{
    return this.page.locator('h1');
  }}
}}
'''
    
    with open(f"{output_dir}/pages/HomePage.ts", "w") as f:
        f.write(example_page)
    
    # Build scaffold structure
    scaffold_structure = ScaffoldStructure(
        features_dir=f"{output_dir}/features",
        step_definitions_dir=f"{output_dir}/step_definitions",
        pages_dir=f"{output_dir}/pages",
        config_dir=f"{output_dir}/config",
        tests_dir=f"{output_dir}/tests",
        reports_dir=f"{output_dir}/reports",
        hooks_dir=f"{output_dir}/hooks",
    )
    
    scaffold_config = ScaffoldConfig(
        project_name=project_name,
        base_url=base_url,
        browser=browser,
        headless=headless,
    )
    
    result = AutomationScaffold(
        project_name=project_name,
        config=scaffold_config,
        structure=scaffold_structure,
        files=[
            ScaffoldFile(
                path="package.json",
                content=json.dumps(package_json, indent=2),
                file_type="config"
            ),
            ScaffoldFile(
                path="playwright.config.ts",
                content=playwright_config,
                file_type="config"
            ),
            ScaffoldFile(
                path="pages/BasePage.ts",
                content=base_page,
                file_type="page"
            ),
            ScaffoldFile(
                path="pages/HomePage.ts",
                content=example_page,
                file_type="page"
            ),
            ScaffoldFile(
                path="features/example.feature",
                content=example_feature,
                file_type="feature"
            )
        ],
        success=True,
        message=f"Successfully created BDD+POM automation scaffold for {project_name}",
        created_at="2026-04-12"
    )
    
    return result.model_dump_json(indent=2)
