"""
Judge Agent Tools
==================

Helpers for confidence scoring and DoD checklist evaluation.
"""

import re

from agno.exceptions import RetryAgentRun, StopAgentRun
from agno.tools import Toolkit, tool


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


# ---------------------------------------------------------------------------
# JudgeToolkit
# ---------------------------------------------------------------------------
class JudgeToolkit(Toolkit):
    """Groups all Judge Agent tools into a single registerable toolkit."""

    def __init__(self) -> None:
        super().__init__(
            name="judge",
            tools=[lint_gherkin, check_code_quality, score_confidence],
        )
