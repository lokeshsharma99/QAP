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

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, WebSocket, WebSocketDisconnect
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
                f"npx cucumber-js --require-module ts-node/register --config cucumber.conf.ts --tags '{body.tags}'"
                " --format @cucumber/html-formatter:reports/cucumber-report.html"
                " --format json:reports/cucumber-report.json"
            )
        cmd = ["docker", "exec", "--workdir", "/app/automation", "qap-api", "sh", "-c", inner_cmd]
    else:
        if body.tags:
            cmd = [
                "npx", "cucumber-js",
                "--require-module", "ts-node/register",
                "--config", "cucumber.conf.ts",
                "--tags", body.tags,
                "--format", "@cucumber/html-formatter:reports/cucumber-report.html",
                "--format", "json:reports/cucumber-report.json",
            ]
        else:
            cmd = ["npm", "run", "test:regression"]

    # Ensure reports directory exists so Cucumber can write its output
    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        proc = subprocess.run(
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
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Run finished but no report was written",
                "returncode": proc.returncode,
                "stdout": proc.stdout[-4000:] if proc.stdout else "",
                "stderr": proc.stderr[-4000:] if proc.stderr else "",
            },
        )
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


# ---------------------------------------------------------------------------
# WS /automation/run/stream — real-time streaming of test execution output
# ---------------------------------------------------------------------------

def _build_run_cmd(tags: str, use_docker: bool) -> list[str]:
    """Build the npx / docker exec command for a test run."""
    if use_docker:
        inner = "npm run test:regression"
        if tags:
            inner = (
                f"npx cucumber-js --require-module ts-node/register --config cucumber.conf.ts --tags '{tags}'"
                " --format @cucumber/html-formatter:reports/cucumber-report.html"
                " --format json:reports/cucumber-report.json"
            )
        return ["docker", "exec", "--workdir", "/app/automation", "qap-api", "sh", "-c", inner]
    if tags:
        return [
            "npx", "cucumber-js",
            "--require-module", "ts-node/register",
            "--config", "cucumber.conf.ts",
            "--tags", tags,
            "--format", "@cucumber/html-formatter:reports/cucumber-report.html",
            "--format", "json:reports/cucumber-report.json",
        ]
    return ["npm", "run", "test:regression"]


@router.websocket("/run/stream")
async def stream_run(
    websocket: WebSocket,
    tags: str = Query(""),
    use_docker: bool = Query(False),
    timeout_seconds: int = Query(300),
):
    """Stream test execution output line-by-line over WebSocket.

    Messages sent to the client are JSON objects:
        { "type": "line",   "data": "<stdout/stderr line>" }
        { "type": "result", "summary": { ...ReportSummary... } }
        { "type": "error",  "detail": "..." }
    """
    await websocket.accept()

    if not _AUTOMATION_DIR.exists():
        await websocket.send_text(json.dumps({"type": "error", "detail": "automation/ directory not found"}))
        await websocket.close()
        return

    if not (_AUTOMATION_DIR / "node_modules").exists():
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "node_modules not found — run npm install in automation/ first.",
        }))
        await websocket.close()
        return

    _REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    cmd = _build_run_cmd(tags, use_docker)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(_AUTOMATION_DIR),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError as exc:
        await websocket.send_text(json.dumps({"type": "error", "detail": f"Command not found: {exc}"}))
        await websocket.close()
        return

    async def _read_lines() -> None:
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            try:
                await websocket.send_text(json.dumps({"type": "line", "data": line}))
            except WebSocketDisconnect:
                proc.kill()
                return

    try:
        await asyncio.wait_for(_read_lines(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        proc.kill()
        await websocket.send_text(json.dumps({"type": "error", "detail": f"Run timed out after {timeout_seconds}s"}))
        await websocket.close()
        return
    except WebSocketDisconnect:
        proc.kill()
        return

    await proc.wait()

    result = _parse_last_report()
    if result is None:
        await websocket.send_text(json.dumps({
            "type": "error",
            "detail": "Run finished but no report was written — check the output above for errors.",
        }))
    else:
        await websocket.send_text(json.dumps({"type": "result", "summary": result}))

    try:
        await websocket.close()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# GET /automation/files/content — serve a single file's text
# ---------------------------------------------------------------------------

_ALLOWED_DIRS = [_FEATURES_DIR, _STEP_DEFS_DIR, _PAGES_DIR, _HOOKS_DIR]
_ALLOWED_EXTS = {".feature", ".ts", ".js", ".json", ".md"}


def _resolve_safe_path(rel_path: str) -> Path:
    """Resolve a relative automation/ path, blocking path-traversal attempts."""
    # Normalise separators
    rel_clean = rel_path.replace("\\", "/").lstrip("/")
    resolved = (_AUTOMATION_DIR / rel_clean).resolve()
    # Must stay inside automation/
    if not str(resolved).startswith(str(_AUTOMATION_DIR.resolve())):
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    if resolved.suffix not in _ALLOWED_EXTS:
        raise HTTPException(status_code=400, detail=f"File type not allowed: {resolved.suffix}")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {rel_clean}")
    return resolved


@router.get("/files/content")
def get_file_content(path: str = Query(..., description="Relative path inside automation/")):
    """Return the text content of a file inside automation/."""
    resolved = _resolve_safe_path(path)
    return {"path": path, "content": resolved.read_text(encoding="utf-8", errors="replace")}


# ---------------------------------------------------------------------------
# File edit-request — pending edit is stored as JSON, applied on approval
# ---------------------------------------------------------------------------

_PENDING_EDITS_FILE = _AUTOMATION_DIR / ".pending-edits.json"


def _load_pending_edits() -> list[dict]:
    if not _PENDING_EDITS_FILE.exists():
        return []
    try:
        return json.loads(_PENDING_EDITS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save_pending_edits(edits: list[dict]) -> None:
    _AUTOMATION_DIR.mkdir(parents=True, exist_ok=True)
    _PENDING_EDITS_FILE.write_text(json.dumps(edits, indent=2), encoding="utf-8")


class EditRequest(BaseModel):
    path: str
    content: str
    comment: str = ""


class EditItem(BaseModel):
    id: str
    path: str
    original_content: str
    new_content: str
    comment: str
    status: str        # pending | approved | rejected
    created_at: str


@router.post("/files/edit-request", response_model=EditItem)
def request_file_edit(body: EditRequest):
    """Submit a file edit for approval. The file is NOT modified until approved."""
    resolved = _resolve_safe_path(body.path)
    original = resolved.read_text(encoding="utf-8", errors="replace")

    import datetime, secrets
    edit_id = secrets.token_hex(8)
    item: dict = {
        "id": edit_id,
        "path": body.path,
        "original_content": original,
        "new_content": body.content,
        "comment": body.comment,
        "status": "pending",
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
    }
    edits = _load_pending_edits()
    # Remove any existing pending edit for the same path
    edits = [e for e in edits if not (e["path"] == body.path and e["status"] == "pending")]
    edits.append(item)
    _save_pending_edits(edits)
    return EditItem(**item)


@router.get("/files/edit-requests", response_model=list[EditItem])
def list_edit_requests(status: Optional[str] = Query(None)):
    """Return pending (or all) file edit requests."""
    edits = _load_pending_edits()
    if status:
        edits = [e for e in edits if e.get("status") == status]
    return [EditItem(**e) for e in edits]


@router.post("/files/edit-requests/{edit_id}/approve", response_model=EditItem)
def approve_edit_request(edit_id: str):
    """Apply the pending edit to disk and mark it approved."""
    edits = _load_pending_edits()
    item = next((e for e in edits if e["id"] == edit_id), None)
    if not item:
        raise HTTPException(status_code=404, detail=f"Edit request {edit_id} not found")
    if item["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Edit request is already {item['status']}")

    resolved = _resolve_safe_path(item["path"])
    resolved.write_text(item["new_content"], encoding="utf-8")

    item["status"] = "approved"
    _save_pending_edits(edits)
    return EditItem(**item)


@router.post("/files/edit-requests/{edit_id}/reject", response_model=EditItem)
def reject_edit_request(edit_id: str):
    """Reject the pending edit without modifying the file."""
    edits = _load_pending_edits()
    item = next((e for e in edits if e["id"] == edit_id), None)
    if not item:
        raise HTTPException(status_code=404, detail=f"Edit request {edit_id} not found")
    if item["status"] != "pending":
        raise HTTPException(status_code=409, detail=f"Edit request is already {item['status']}")

    item["status"] = "rejected"
    _save_pending_edits(edits)
    return EditItem(**item)
