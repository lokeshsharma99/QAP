"""
Judge Agent Tools
==================

Helpers for confidence scoring and DoD checklist evaluation.
"""

import json
import os
import re
import subprocess
from pathlib import Path

import requests

from agno.exceptions import RetryAgentRun, StopAgentRun
from agno.tools import Toolkit, tool

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_AUTOMATION_DIR = _PROJECT_ROOT / "automation"


@tool(
    name="lint_gherkin",
    description="Run a basic Gherkin syntax check on feature file content. Returns a dict of check name → pass/fail.",
)
def lint_gherkin(content: str) -> dict[str, bool]:
    """Run a basic Gherkin syntax check on feature file content.

    Args:
        content: Raw Gherkin feature file text.

    Returns:
        Dict of check name → pass/fail.
    """
    if not content or not content.strip():
        raise RetryAgentRun(
            "Empty content provided to lint_gherkin. Retrieve the Gherkin feature file content and try again."
        )

    results: dict[str, bool] = {}

    results["has_feature"] = bool(re.search(r"^\s*Feature:", content, re.MULTILINE))
    results["has_scenario"] = bool(re.search(r"^\s*Scenario:", content, re.MULTILINE))
    results["has_given"] = bool(re.search(r"^\s*Given\s", content, re.MULTILINE))
    results["has_when"] = bool(re.search(r"^\s*When\s", content, re.MULTILINE))
    results["has_then"] = bool(re.search(r"^\s*Then\s", content, re.MULTILINE))
    results["has_ac_tags"] = bool(re.search(r"@AC-\d+", content))
    results["no_technical_jargon"] = not bool(
        re.search(r"data-testid|\.click\(\)|\.fill\(|querySelector|xpath", content, re.IGNORECASE)
    )

    if not results["has_feature"] and not results["has_scenario"]:
        raise RetryAgentRun(
            "Content is not valid Gherkin — missing both Feature: and Scenario: keywords. "
            "Ensure you are passing a valid .feature file and try again."
        )

    return results


@tool(
    name="check_code_quality",
    description="Run a basic TypeScript/Playwright code quality check. Returns a dict of check name → pass/fail.",
)
def check_code_quality(content: str) -> dict[str, bool]:
    """Run a basic TypeScript/Playwright code quality check.

    Args:
        content: TypeScript source code content.

    Returns:
        Dict of check name → pass/fail.
    """
    if not content or not content.strip():
        raise RetryAgentRun(
            "Empty content provided to check_code_quality. Retrieve the TypeScript source file and try again."
        )

    results: dict[str, bool] = {}

    results["no_sleep"] = not bool(
        re.search(r"sleep\(|waitForTimeout\(|setTimeout\(|setInterval\(", content)
    )
    results["no_hardcoded_data"] = not bool(
        re.search(r'(email|password|username)\s*=\s*["\'][^"\']+["\']', content, re.IGNORECASE)
    )
    results["uses_testid_or_role"] = bool(
        re.search(r"getByTestId|getByRole|getByText|data-testid", content)
    )
    results["no_xpath"] = not bool(re.search(r"xpath|//div|//span|//input", content))
    results["has_class"] = bool(re.search(r"class\s+\w+Page", content))

    return results


@tool(
    name="score_confidence",
    description=(
        "Calculate confidence score from DoD checklist results. "
        "Raises StopAgentRun (AUTO-REJECT) when score < 0.50."
    ),
)
def score_confidence(checklist_results: dict[str, bool], artifact_type: str) -> float:
    """Calculate confidence score from checklist results.

    Args:
        checklist_results: Dict of check name → pass/fail.
        artifact_type: "gherkin" | "code" | "data" | "healing"

    Returns:
        Confidence score between 0.0 and 1.0.

    Raises:
        StopAgentRun: When score < 0.50 (AUTO-REJECT per quality gate policy).
    """
    if not checklist_results:
        raise StopAgentRun(
            "AUTO-REJECT: No checklist results provided — cannot score artifact. "
            "Run lint_gherkin or check_code_quality first."
        )

    total = len(checklist_results)
    passed = sum(1 for v in checklist_results.values() if v)
    base_score = passed / total

    # Critical failure caps
    critical_failures = {
        "gherkin": {"all_acs_covered": 0.60, "syntax_valid": 0.50},
        "code": {"no_hardcoded_sleep": 0.50, "no_hardcoded_data": 0.55},
        "healing": {"only_locator_changed": 0.40, "verification_3x": 0.45},
    }

    caps = critical_failures.get(artifact_type, {})
    for check, cap in caps.items():
        if check in checklist_results and not checklist_results[check]:
            base_score = min(base_score, cap)

    final_score = round(base_score, 2)

    if final_score < 0.50:
        raise StopAgentRun(
            f"AUTO-REJECT: Confidence score {final_score:.0%} is below the 50% threshold. "
            f"Artifact type: {artifact_type}. Failed checks: "
            f"{[k for k, v in checklist_results.items() if not v]}. "
            "Sending artifact back to the producing agent for rework."
        )

    return final_score


@tool(
    name="run_eslint_check",
    description=(
        "Run ESLint on a TypeScript file or the whole automation/ directory. "
        "Returns error_count, warning_count, and a list of violations. "
        "Use this as a mandatory DoD check on every generated .ts file."
    ),
)
def run_eslint_check(file_path: str = "") -> dict:
    """Run ESLint on a TypeScript file (relative to automation/) or the whole automation/ dir.

    Args:
        file_path: Relative path within automation/ (e.g. "pages/login.page.ts").
                   Leave empty for the full automation/ directory.

    Returns:
        dict: status ("PASS"|"FAIL"|"ERROR"), error_count, warning_count, errors list.
    """
    if not _AUTOMATION_DIR.exists():
        return {"status": "ERROR", "error": "automation/ directory not found"}
    if not (_AUTOMATION_DIR / "node_modules").exists():
        return {"status": "ERROR", "error": "node_modules not found. Run 'npm install' in automation/."}

    target = str(_AUTOMATION_DIR / file_path) if file_path else "."
    cmd = ["npx", "eslint", "--ext", ".ts", "--format", "json", target]

    try:
        result = subprocess.run(cmd, cwd=str(_AUTOMATION_DIR), capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        return {"status": "ERROR", "error": "npx not found"}
    except subprocess.TimeoutExpired:
        return {"status": "ERROR", "error": "ESLint timed out"}

    error_count = 0
    warning_count = 0
    errors_list: list[dict] = []

    try:
        lint_data = json.loads(result.stdout or "[]")
        for file_result in lint_data:
            for msg in file_result.get("messages", []):
                severity = msg.get("severity", 1)
                entry = {
                    "file": file_result.get("filePath", ""),
                    "line": msg.get("line"),
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
        return {"status": "ERROR", "error": f"ESLint output parse failed: {result.stderr}"}

    return {
        "status": "PASS" if error_count == 0 else "FAIL",
        "error_count": error_count,
        "warning_count": warning_count,
        "errors": errors_list,
    }


@tool(
    name="check_sonar_quality_gate",
    description=(
        "Query SonarQube/SonarCloud for the quality gate status of the automation framework project. "
        "Returns pass/fail + issues breakdown (bugs, vulnerabilities, code smells, coverage). "
        "Requires SONAR_URL and SONAR_TOKEN env vars. Skips gracefully if SonarQube is not running."
    ),
)
def check_sonar_quality_gate(project_key: str = "") -> dict:
    """Check the SonarQube quality gate for the automation project.

    Connects to local SonarQube (default: http://localhost:9000) or SonarCloud.
    If SonarQube is unreachable, returns a skipped result so the pipeline continues.

    Args:
        project_key: SonarQube project key (defaults to SONAR_PROJECT_KEY env var or
                     "quality-autopilot-automation").

    Returns:
        dict: status ("PASS"|"FAIL"|"SKIPPED"), gate_status, metrics breakdown.
    """
    sonar_url = os.getenv("SONAR_URL", "http://localhost:9000").rstrip("/")
    sonar_token = os.getenv("SONAR_TOKEN", "")
    key = project_key or os.getenv("SONAR_PROJECT_KEY", "quality-autopilot-automation")

    if not sonar_token:
        return {
            "status": "SKIPPED",
            "reason": "SONAR_TOKEN not set — configure SonarQube to enable quality gate checks",
        }

    auth = (sonar_token, "") if sonar_token else None
    timeout = 10

    try:
        # Quality gate status
        gate_resp = requests.get(
            f"{sonar_url}/api/qualitygates/project_status",
            params={"projectKey": key},
            auth=auth,
            timeout=timeout,
        )
        gate_resp.raise_for_status()
        gate_data = gate_resp.json().get("projectStatus", {})
        gate_status = gate_data.get("status", "UNKNOWN")  # OK | WARN | ERROR

        # Key metrics
        metrics_resp = requests.get(
            f"{sonar_url}/api/measures/component",
            params={
                "component": key,
                "metricKeys": "bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density,sqale_rating",
            },
            auth=auth,
            timeout=timeout,
        )
        metrics_resp.raise_for_status()
        measures = {
            m["metric"]: m.get("value", "N/A")
            for m in metrics_resp.json().get("component", {}).get("measures", [])
        }

        # Issues summary
        issues_resp = requests.get(
            f"{sonar_url}/api/issues/search",
            params={"componentKeys": key, "severities": "BLOCKER,CRITICAL", "resolved": "false", "ps": 10},
            auth=auth,
            timeout=timeout,
        )
        issues_resp.raise_for_status()
        critical_issues = [
            {"severity": i["severity"], "message": i["message"], "component": i["component"]}
            for i in issues_resp.json().get("issues", [])
        ]

        passed = gate_status == "OK"
        return {
            "status": "PASS" if passed else "FAIL",
            "gate_status": gate_status,
            "project_key": key,
            "sonar_url": sonar_url,
            "metrics": measures,
            "critical_issues": critical_issues,
            "dashboard_url": f"{sonar_url}/dashboard?id={key}",
        }

    except requests.exceptions.ConnectionError:
        return {
            "status": "SKIPPED",
            "reason": f"SonarQube not reachable at {sonar_url}. Start with: docker compose --profile sonar up -d",
        }
    except requests.exceptions.HTTPError as exc:
        return {
            "status": "ERROR",
            "reason": f"SonarQube API error: {exc}",
        }
    except Exception as exc:
        return {
            "status": "SKIPPED",
            "reason": f"SonarQube check skipped: {exc}",
        }


# ---------------------------------------------------------------------------
# JudgeToolkit
# ---------------------------------------------------------------------------
class JudgeToolkit(Toolkit):
    """Groups all Judge Agent tools into a single registerable toolkit."""

    def __init__(self) -> None:
        super().__init__(
            name="judge",
            tools=[lint_gherkin, check_code_quality, score_confidence, run_eslint_check, check_sonar_quality_gate],
        )
