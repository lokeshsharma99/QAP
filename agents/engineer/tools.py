"""
Engineer Agent Tools
=====================

Code generation, linting, file system, and test execution tools for the Engineer Agent.
"""

import json
import subprocess
from pathlib import Path

# Project root (two levels up from agents/engineer/)
_PROJECT_ROOT = Path(__file__).parent.parent.parent
_AUTOMATION_DIR = _PROJECT_ROOT / "automation"


def write_pom(file_path: str, content: str) -> str:
    """Write a Page Object Model TypeScript file to automation/pages/.

    Args:
        file_path: Relative path within automation/pages/ (e.g., "login.page.ts")
        content: Full TypeScript class content.

    Returns:
        Confirmation message with the written file path.
    """
    base = _AUTOMATION_DIR / "pages"
    target = base / file_path

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written POM: automation/pages/{file_path}"


def write_step_def(file_path: str, content: str) -> str:
    """Write a Step Definition TypeScript file to automation/step_definitions/.

    Args:
        file_path: Relative path within automation/step_definitions/ (e.g., "login.steps.ts")
        content: Full TypeScript step definition content.

    Returns:
        Confirmation message with the written file path.
    """
    base = _AUTOMATION_DIR / "step_definitions"
    target = base / file_path

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written step defs: automation/step_definitions/{file_path}"


def write_feature(file_path: str, content: str) -> str:
    """Write a Gherkin feature file to automation/features/.

    Args:
        file_path: Relative path within automation/features/ (e.g., "login.feature")
        content: Full Gherkin feature file content.

    Returns:
        Confirmation message with the written file path.
    """
    base = _AUTOMATION_DIR / "features"
    target = base / file_path

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written feature: automation/features/{file_path}"


def run_typecheck(working_dir: str = "automation") -> str:
    """Run TypeScript type-check on the automation framework.

    Args:
        working_dir: Directory to run tsc in (relative to project root).

    Returns:
        'PASS' message or error output from tsc.
    """
    target = _PROJECT_ROOT / working_dir
    if not (target / "tsconfig.json").exists():
        return f"ERROR: tsconfig.json not found in {working_dir}"

    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=str(target),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return "PASS: TypeScript type-check succeeded"
        return f"FAIL: Type errors found:\n{result.stdout}\n{result.stderr}"
    except FileNotFoundError:
        return "ERROR: npx not found. Run 'npm install' in automation/ first."
    except subprocess.TimeoutExpired:
        return "ERROR: tsc timed out after 60s"


# ---------------------------------------------------------------------------
# Test execution tools
# ---------------------------------------------------------------------------

def run_tests(tags: str = "", timeout_seconds: int = 300, use_docker: bool = False) -> dict:
    """Execute the Cucumber/Playwright regression suite.

    By default runs inside the current process (inside qap-api container which has Node.js).
    Set use_docker=True to delegate to the dedicated qap-playwright container — this gives
    full browser sandboxing and is required when qap-api has no Playwright browsers installed.

    The report is always written to automation/reports/cucumber-report.json.
    Trace ZIPs for failures land in automation/test-results/ and are picked up by the Detective.

    Args:
        tags: Optional Cucumber tag expression (e.g. "@smoke" or "@AC-001").
              Leave empty to run the full suite.
        timeout_seconds: Max seconds before the run is killed (default: 5 min).
        use_docker: If True, run inside the qap-playwright Docker container.

    Returns:
        dict with keys: passed, failed, pending, total, status, report_path,
        html_report, trace_dir, failures (list of dicts with scenario + error).
    """
    if not _AUTOMATION_DIR.exists():
        return {"status": "ERROR", "error": "automation/ directory not found"}

    if use_docker:
        # Delegate to the qap-playwright container (requires --profile runner)
        inner_cmd = "npm run test:regression"
        if tags:
            inner_cmd = (
                f"npx cucumber-js --config cucumber.conf.ts --tags '{tags}'"
                " --format @cucumber/html-formatter:reports/cucumber-report.html"
                " --format json:reports/cucumber-report.json"
            )
        cmd = ["docker", "exec", "qap-playwright", "sh", "-c", inner_cmd]
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            return {"status": "ERROR", "error": f"Docker test run timed out after {timeout_seconds}s"}
        except FileNotFoundError:
            return {"status": "ERROR", "error": "docker CLI not found"}
        result = parse_test_report()
        result["trace_dir"] = str(_AUTOMATION_DIR / "test-results")
        return result

    # Run inside the current container (qap-api has Node.js from the Dockerfile)
    if not (_AUTOMATION_DIR / "node_modules").exists():
        return {
            "status": "ERROR",
            "error": "node_modules not found. Run 'npm install' in automation/ first.",
        }

    cmd = ["npm", "run", "test:regression"]
    if tags:
        cmd = [
            "npx", "cucumber-js",
            "--config", "cucumber.conf.ts",
            "--tags", tags,
            "--format", "@cucumber/html-formatter:reports/cucumber-report.html",
            "--format", "json:reports/cucumber-report.json",
        ]

    try:
        subprocess.run(
            cmd,
            cwd=str(_AUTOMATION_DIR),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return {"status": "ERROR", "error": f"Test run timed out after {timeout_seconds}s"}
    except FileNotFoundError:
        return {"status": "ERROR", "error": "npm not found. Node.js must be installed."}

    result = parse_test_report()
    result["trace_dir"] = str(_AUTOMATION_DIR / "test-results")
    return result


def parse_test_report(report_path: str = "reports/cucumber-report.json") -> dict:
    """Parse a Cucumber JSON report and extract pass/fail summary + failure details.

    Args:
        report_path: Path relative to automation/ (default: reports/cucumber-report.json).

    Returns:
        dict with: passed, failed, pending, total, status, report_path, failures list.
        Each failure has: scenario, feature, step, error, screenshot (if attached).
    """
    full_path = _AUTOMATION_DIR / report_path
    if not full_path.exists():
        return {
            "status": "ERROR",
            "error": f"Report not found at {full_path}. Run tests first.",
        }

    try:
        report_data = json.loads(full_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "ERROR", "error": f"Could not parse report JSON: {exc}"}

    passed = failed = pending = 0
    failures: list[dict] = []

    for feature in report_data:
        feature_name = feature.get("name", "unknown feature")
        for element in feature.get("elements", []):
            scenario_name = element.get("name", "unknown scenario")
            scenario_status = "passed"
            for step in element.get("steps", []):
                result = step.get("result", {})
                step_status = result.get("status", "passed")
                if step_status == "failed":
                    scenario_status = "failed"
                    failures.append({
                        "feature": feature_name,
                        "scenario": scenario_name,
                        "step": step.get("name", ""),
                        "error": result.get("error_message", "no error message"),
                    })
                elif step_status == "pending":
                    scenario_status = "pending"

            if scenario_status == "passed":
                passed += 1
            elif scenario_status == "failed":
                failed += 1
            else:
                pending += 1

    total = passed + failed + pending
    overall = "PASS" if failed == 0 and total > 0 else ("FAIL" if failed > 0 else "NO_TESTS")

    return {
        "status": overall,
        "passed": passed,
        "failed": failed,
        "pending": pending,
        "total": total,
        "report_path": str(full_path),
        "html_report": str(_AUTOMATION_DIR / "reports" / "cucumber-report.html"),
        "failures": failures,
    }


def write_run_context(ticket_id: str, content: str) -> str:
    """Write a RunContext JSON file to automation/data/.

    Args:
        ticket_id: Jira/ADO ticket ID used as filename stem (e.g. "PROJ-001").
        content: JSON string of the RunContext.

    Returns:
        Confirmation message with the written file path.
    """
    base = _AUTOMATION_DIR / "data"
    base.mkdir(parents=True, exist_ok=True)
    target = base / f"{ticket_id}.json"
    target.write_text(content, encoding="utf-8")
    return f"Written run context: automation/data/{ticket_id}.json"


def run_eslint(file_path: str = "", fix: bool = False) -> dict:
    """Run ESLint on a specific TypeScript file or the whole automation/ directory.

    Call this IMMEDIATELY after writing any .ts file (POM, step def, helper).
    Never declare a file "done" until this returns zero errors.

    Args:
        file_path: Path relative to automation/ (e.g. "pages/login.page.ts").
                   Leave empty to lint the entire automation/ directory.
        fix:       If True, run --fix to auto-correct fixable issues first.

    Returns:
        dict with: status ("PASS"|"FAIL"|"ERROR"), error_count, warning_count,
                   errors (list of {file, line, col, rule, message}).
    """
    if not _AUTOMATION_DIR.exists():
        return {"status": "ERROR", "error": "automation/ directory not found"}
    if not (_AUTOMATION_DIR / "node_modules").exists():
        return {"status": "ERROR", "error": "node_modules not found. Run 'npm install' first."}

    target = str(_AUTOMATION_DIR / file_path) if file_path else "."

    cmd = ["npx", "eslint", "--ext", ".ts", "--format", "json"]
    if fix:
        cmd.append("--fix")
    cmd.append(target)

    try:
        result = subprocess.run(cmd, cwd=str(_AUTOMATION_DIR), capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return {"status": "ERROR", "error": "npx not found. Node.js must be installed."}
    except subprocess.TimeoutExpired:
        return {"status": "ERROR", "error": "ESLint timed out after 60s"}

    # Parse JSON output
    errors_list: list[dict] = []
    error_count = 0
    warning_count = 0
    try:
        lint_data = json.loads(result.stdout or "[]")
        for file_result in lint_data:
            file_rel = str(Path(file_result.get("filePath", "")).relative_to(_AUTOMATION_DIR))
            for msg in file_result.get("messages", []):
                severity = msg.get("severity", 1)
                entry = {
                    "file": file_rel,
                    "line": msg.get("line"),
                    "col": msg.get("column"),
                    "rule": msg.get("ruleId", ""),
                    "message": msg.get("message", ""),
                    "severity": "error" if severity == 2 else "warning",
                }
                if severity == 2:
                    error_count += 1
                    errors_list.append(entry)
                else:
                    warning_count += 1
    except (json.JSONDecodeError, ValueError):
        # ESLint can emit non-JSON if there's a config error
        return {
            "status": "ERROR",
            "error": f"Failed to parse ESLint output: {result.stderr or result.stdout}",
        }

    status = "PASS" if error_count == 0 else "FAIL"
    return {
        "status": status,
        "error_count": error_count,
        "warning_count": warning_count,
        "errors": errors_list,
        "fixed": fix and result.returncode == 0,
    }


def run_ruff(file_path: str = "", fix: bool = False) -> dict:
    """Run ruff linter + formatter on a specific Python file or the whole project.

    Use for any Python file generated by agents (tools.py, agent.py, etc.).

    Args:
        file_path: Absolute or project-relative path to a .py file or directory.
                   Leave empty to lint the whole project root.
        fix:       If True, run --fix to auto-correct fixable issues.

    Returns:
        dict with: status ("PASS"|"FAIL"|"ERROR"), violation_count,
                   violations (list of {file, line, col, code, message}).
    """
    target = str(_PROJECT_ROOT / file_path) if file_path else str(_PROJECT_ROOT)

    check_cmd = ["ruff", "check", "--output-format=json"]
    if fix:
        check_cmd.append("--fix")
    check_cmd.append(target)

    format_cmd = ["ruff", "format", "--check", target]

    violations: list[dict] = []
    format_issues: list[str] = []

    try:
        check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=60)
        fmt_result = subprocess.run(format_cmd, capture_output=True, text=True, timeout=30)
    except FileNotFoundError:
        return {"status": "ERROR", "error": "ruff not found. Install: pip install ruff"}
    except subprocess.TimeoutExpired:
        return {"status": "ERROR", "error": "ruff timed out"}

    try:
        ruff_data = json.loads(check_result.stdout or "[]")
        for item in ruff_data:
            violations.append({
                "file": item.get("filename", ""),
                "line": item.get("location", {}).get("row"),
                "col": item.get("location", {}).get("column"),
                "code": item.get("code", ""),
                "message": item.get("message", ""),
                "fixable": item.get("fix") is not None,
            })
    except (json.JSONDecodeError, ValueError):
        pass  # ruff may emit plain text if config is broken

    if fmt_result.returncode != 0 and fmt_result.stdout:
        format_issues = [l for l in fmt_result.stdout.splitlines() if "would reformat" in l]

    status = "PASS" if not violations and not format_issues else "FAIL"
    return {
        "status": status,
        "violation_count": len(violations),
        "format_issues": format_issues,
        "violations": violations[:30],  # cap to avoid flooding context
    }

