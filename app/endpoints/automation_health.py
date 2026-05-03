"""
Automation Health API
=====================

REST endpoints that let the Control Plane UI inspect the state of the
automation/ test framework and trigger runs on demand.

Routes:
    GET  /automation/health      — scan feature files, step defs, pages + last report
    GET  /automation/report      — latest cucumber-report.json (raw or parsed)
    POST /automation/run         — trigger a test run (sync, streams result when done)
    GET  /automation/traces      — list trace ZIPs available for Detective analysis
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/automation", tags=["automation"])

# ---------------------------------------------------------------------------
# Paths (relative to the project root — same as engineer/tools.py)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # tests/
_AUTOMATION_DIR = _PROJECT_ROOT / "automation"
_REPORTS_DIR = _AUTOMATION_DIR / "reports"
_TRACES_DIR = _AUTOMATION_DIR / "test-results"
_FEATURES_DIR = _AUTOMATION_DIR / "features"
_STEP_DEFS_DIR = _AUTOMATION_DIR / "step_definitions"
_PAGES_DIR = _AUTOMATION_DIR / "pages"
_HOOKS_DIR = _AUTOMATION_DIR / "hooks"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class FeatureSummary(BaseModel):
    path: str
    name: str
    scenario_count: int
    tag_count: int
    tags: list[str]


class StepDefSummary(BaseModel):
    path: str
    step_count: int


class PageObjectSummary(BaseModel):
    path: str
    name: str


class AutomationHealth(BaseModel):
    status: str                          # "healthy" | "degraded" | "no_tests"
    features: list[FeatureSummary]
    step_definitions: list[StepDefSummary]
    page_objects: list[PageObjectSummary]
    total_scenarios: int
    total_steps: int
    total_pages: int
    npm_installed: bool
    last_report_summary: Optional[dict]
    node_modules_present: bool


class RunRequest(BaseModel):
    tags: str = ""
    use_docker: bool = False
    timeout_seconds: int = 300


class TraceFile(BaseModel):
    name: str
    path: str
    size_kb: float
    modified: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _count_scenarios_in_feature(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip().startswith(("Scenario:", "Scenario Outline:")))


def _extract_tags_from_feature(text: str) -> list[str]:
    tags: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("@"):
            tags.extend(stripped.split())
    return list(set(tags))


def _count_step_bindings(text: str) -> int:
    """Count @Given / @When / @Then / @And / @But decorators in a TS file."""
    count = 0
    for line in text.splitlines():
        stripped = line.strip()
        if any(stripped.startswith(f"{d}(") for d in ("Given", "When", "Then", "And", "But")):
            count += 1
    return count


def _parse_last_report() -> Optional[dict]:
    report_path = _REPORTS_DIR / "cucumber-report.json"
    if not report_path.exists():
        return None
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
        passed = failed = pending = 0
        failures: list[dict] = []
        for feature in data:
            for element in feature.get("elements", []):
                scenario_name = element.get("name", "unknown")
                scenario_failed = False
                for step in element.get("steps", []):
                    result = step.get("result", {})
                    status = result.get("status", "unknown")
                    if status == "passed":
                        passed += 1
                    elif status == "failed":
                        failed += 1
                        scenario_failed = True
                        if not any(f["scenario"] == scenario_name for f in failures):
                            failures.append({
                                "feature": feature.get("name", ""),
                                "scenario": scenario_name,
                                "error": result.get("error_message", "")[:300],
                            })
                    elif status in ("pending", "undefined"):
                        pending += 1
                if scenario_failed:
                    pass  # already counted above
        total = passed + failed + pending
        return {
            "status": "PASS" if failed == 0 and total > 0 else ("FAIL" if failed > 0 else "NO_RUNS"),
            "passed": passed,
            "failed": failed,
            "pending": pending,
            "total": total,
            "failures": failures[:10],
            "report_path": str(report_path),
        }
    except Exception as exc:
        return {"status": "ERROR", "error": str(exc)}


# ---------------------------------------------------------------------------
# GET /automation/health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=AutomationHealth)
def get_automation_health():
    """Scan the automation/ folder and return framework health status."""
    if not _AUTOMATION_DIR.exists():
        raise HTTPException(status_code=404, detail="automation/ directory not found")

    # --- Feature files ---
    features: list[FeatureSummary] = []
    total_scenarios = 0
    for f in sorted(_FEATURES_DIR.rglob("*.feature")) if _FEATURES_DIR.exists() else []:
        text = f.read_text(encoding="utf-8", errors="ignore")
        sc_count = _count_scenarios_in_feature(text)
        tags = _extract_tags_from_feature(text)
        features.append(FeatureSummary(
            path=str(f.relative_to(_AUTOMATION_DIR)),
            name=f.stem,
            scenario_count=sc_count,
            tag_count=len(tags),
            tags=tags,
        ))
        total_scenarios += sc_count

    # --- Step definitions ---
    step_defs: list[StepDefSummary] = []
    total_steps = 0
    for f in sorted(_STEP_DEFS_DIR.rglob("*.ts")) if _STEP_DEFS_DIR.exists() else []:
        text = f.read_text(encoding="utf-8", errors="ignore")
        sc = _count_step_bindings(text)
        step_defs.append(StepDefSummary(
            path=str(f.relative_to(_AUTOMATION_DIR)),
            step_count=sc,
        ))
        total_steps += sc

    # --- Page objects ---
    pages: list[PageObjectSummary] = []
    for f in sorted(_PAGES_DIR.rglob("*.ts")) if _PAGES_DIR.exists() else []:
        pages.append(PageObjectSummary(
            path=str(f.relative_to(_AUTOMATION_DIR)),
            name=f.stem,
        ))

    npm_installed = (_AUTOMATION_DIR / "node_modules").exists()
    last_report = _parse_last_report()

    if not features:
        status = "no_tests"
    elif not step_defs:
        status = "degraded"
    elif last_report and last_report.get("status") == "FAIL":
        status = "degraded"
    else:
        status = "healthy"

    return AutomationHealth(
        status=status,
        features=features,
        step_definitions=step_defs,
        page_objects=pages,
        total_scenarios=total_scenarios,
        total_steps=total_steps,
        total_pages=len(pages),
        npm_installed=npm_installed,
        last_report_summary=last_report,
        node_modules_present=npm_installed,
    )


# ---------------------------------------------------------------------------
# GET /automation/report
# ---------------------------------------------------------------------------

@router.get("/report")
def get_automation_report(raw: bool = Query(False, description="Return raw JSON array if true")):
    """Return the latest Cucumber JSON report (parsed summary or raw)."""
    report_path = _REPORTS_DIR / "cucumber-report.json"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="No test report found. Run the test suite first.")
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to parse report: {exc}") from exc

    if raw:
        return data

    return _parse_last_report()


# ---------------------------------------------------------------------------
# POST /automation/run
# ---------------------------------------------------------------------------

@router.post("/run")
def trigger_run(body: RunRequest, background_tasks: BackgroundTasks):
    """Trigger a Cucumber/Playwright test run.

    Runs synchronously (may take minutes). For a non-blocking experience
    POST then poll GET /automation/report.

    Returns the parsed report summary when complete.
    """
    if not _AUTOMATION_DIR.exists():
        raise HTTPException(status_code=500, detail="automation/ directory not found")

    if not (_AUTOMATION_DIR / "node_modules").exists():
        raise HTTPException(
            status_code=428,
            detail="node_modules not found. Run 'npm install' inside automation/ first.",
        )

    if body.use_docker:
        inner_cmd = "npm run test:regression"
        if body.tags:
            inner_cmd = (
                f"npx cucumber-js --config cucumber.conf.ts --tags '{body.tags}'"
                " --format @cucumber/html-formatter:reports/cucumber-report.html"
                " --format json:reports/cucumber-report.json"
            )
        cmd = ["docker", "exec", "qap-playwright", "sh", "-c", inner_cmd]
    else:
        if body.tags:
            cmd = [
                "npx", "cucumber-js",
                "--config", "cucumber.conf.ts",
                "--tags", body.tags,
                "--format", "@cucumber/html-formatter:reports/cucumber-report.html",
                "--format", "json:reports/cucumber-report.json",
            ]
        else:
            cmd = ["npm", "run", "test:regression"]

    try:
        subprocess.run(
            cmd,
            cwd=str(_AUTOMATION_DIR),
            capture_output=True,
            text=True,
            timeout=body.timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"Run timed out after {body.timeout_seconds}s")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=f"Command not found: {exc}") from exc

    result = _parse_last_report()
    if result is None:
        raise HTTPException(status_code=500, detail="Run finished but no report was written")
    return result


# ---------------------------------------------------------------------------
# GET /automation/traces
# ---------------------------------------------------------------------------

@router.get("/traces", response_model=list[TraceFile])
def list_traces():
    """List all Playwright trace ZIPs available for Detective analysis."""
    if not _TRACES_DIR.exists():
        return []
    traces: list[TraceFile] = []
    for f in sorted(_TRACES_DIR.rglob("trace.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = f.stat()
        traces.append(TraceFile(
            name=str(f.relative_to(_TRACES_DIR)),
            path=str(f),
            size_kb=round(stat.st_size / 1024, 1),
            modified=__import__("datetime").datetime.fromtimestamp(stat.st_mtime).isoformat(),
        ))
    return traces


# ---------------------------------------------------------------------------
# Sync endpoint — manual or git-hook trigger for KB re-indexing
# ---------------------------------------------------------------------------

class SyncResult(BaseModel):
    status: str
    files_indexed: int
    files_changed: list[str]
    message: str


@router.post("/sync", response_model=SyncResult, summary="Re-index automation/ into Knowledge Base")
def sync_automation_kb(background_tasks: BackgroundTasks):
    """Trigger a Knowledge Base re-index of the entire automation/ directory.

    Call this:
    - From a git post-commit hook: `curl -X POST http://localhost:8000/automation/sync`
    - From CI after a PR merge
    - Manually after editing Page Objects or Step Defs

    The indexing runs in the background — the endpoint returns immediately.
    Check /automation/health afterward to see updated file counts.

    The background watcher (watchfiles) also triggers this automatically for
    file saves, but this endpoint provides an explicit on-demand trigger.
    """
    changed: list[str] = []
    try:
        from agents.librarian.tools import index_automation_codebase
        result = index_automation_codebase(watch_path="automation")
        # Parse the result string for file count
        import re
        m = re.search(r"(\d+) files", result)
        count = int(m.group(1)) if m else 0
        return SyncResult(
            status="ok",
            files_indexed=count,
            files_changed=changed,
            message=result,
        )
    except Exception as e:
        return SyncResult(
            status="error",
            files_indexed=0,
            files_changed=[],
            message=str(e),
        )
