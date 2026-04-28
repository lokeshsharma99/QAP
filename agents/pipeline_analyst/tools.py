"""
Pipeline Analyst Tools
======================

Custom Python tools for downloading and parsing CI artifacts from GitHub Actions.
These bridge the gap between the GitHub MCP server (which can only LIST artifacts)
and the actual content needed for precise test failure analysis.

Why the GitHub MCP server is not enough
----------------------------------------
The MCP `actions` toolset provides:
  - list_workflow_runs, get_workflow_run
  - list_jobs_for_workflow_run
  - download_job_logs_for_workflow_run   ← raw text log only
  - list_workflow_run_artifacts          ← metadata only (name, id, size)

It does NOT provide artifact download (binary ZIP blobs).  The exact test error
messages and stack traces live INSIDE the artifact ZIPs — not in the text log.

CI Artifact names for GDS-Demo-App (defined in .github/workflows/ci.yml)
-------------------------------------------------------------------------
  playwright-traces   uploaded only on E2E test FAILURE (if: failure())
                      Contents: test-results/ directory including:
                        - e2e-junit.xml          ← JUnit XML with verbatim errors
                        - **/*-trace.zip         ← Playwright trace archives
                        - **/*.png / **/*.webm   ← screenshots / videos
  playwright-report   always uploaded (single index.html — not machine-parseable)
  allure-results      always uploaded (*-result.json per test case)
  coverage-report     always uploaded (lcov / HTML coverage data)

Disambiguation
--------------
  playwright-traces  → use download_ci_artifact() + parse_junit_xml()
  allure-results     → use download_ci_artifact() + parse_allure_results()

Gap summary resolved by these tools
-------------------------------------
  Gap 1: Playwright traces (trace.zip) were not accessible → download_ci_artifact()
          downloads the ZIP, returns extracted paths including any trace.zip files
          so the Detective agent can run parse_trace_zip() on them.

  Gap 2: Actual error messages not retrieved → parse_junit_xml() / parse_allure_results()
          extract the verbatim error text + full stack trace from the artifact files
          instead of inferring it from the job log.
"""

import json
import os
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

class _StripAuthOnRedirect(urllib.request.HTTPRedirectHandler):
    """Custom redirect handler that drops Authorization when leaving api.github.com.

    GitHub artifact download endpoints return a 302 to Azure Blob Storage.
    Python's urllib blindly forwards all headers (including Authorization) to the
    redirect target, which Azure rejects with AuthenticationFailed 403.
    """

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req is not None:
            import urllib.parse
            if not urllib.parse.urlparse(newurl).netloc.endswith("github.com"):
                new_req.remove_header("Authorization")
                new_req.remove_header("authorization")
        return new_req


def _github_get(url: str, token: str) -> bytes:
    """Authenticated GitHub REST API GET.

    Uses a custom redirect handler so the Authorization token is NOT forwarded
    when GitHub redirects artifact downloads to Azure Blob Storage.
    """
    opener = urllib.request.build_opener(_StripAuthOnRedirect)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with opener.open(req) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} for {url}: {body}") from exc


# ---------------------------------------------------------------------------
# Tool 1 — download_ci_artifact
# ---------------------------------------------------------------------------

def download_ci_artifact(run_id: str, artifact_name: str, output_dir: str = "") -> dict:
    """Download a named GitHub Actions artifact and extract it to disk.

    The GitHub MCP server can only LIST artifacts (name, id, size, expiry).
    This tool performs the actual download via the GitHub REST API, giving the
    Pipeline Analyst access to JUnit XML results, trace.zip files, and screenshots
    that are otherwise invisible.

    Typical usage
    -------------
      # Get JUnit XML + trace.zip files from a failed E2E run
      result = download_ci_artifact(run_id="25033568108", artifact_name="playwright-traces")
      # → result["output_dir"] contains extracted files including e2e-junit.xml
      # Then call parse_junit_xml(result["output_dir"] + "/e2e-junit.xml")
      # Or pass any *-trace.zip paths to the Detective's parse_trace_zip()

      # Get Allure result JSONs (always present, not just on failure)
      result = download_ci_artifact(run_id="25033568108", artifact_name="allure-results")
      # → result["output_dir"] contains *-result.json files
      # Then call parse_allure_results(result["output_dir"])

    Args:
        run_id:        GitHub Actions workflow run ID (string or integer).
        artifact_name: Exact artifact name (e.g. "playwright-traces",
                       "allure-results", "playwright-report", "coverage-report").
        output_dir:    Directory to extract files into.  Defaults to a new
                       temporary directory (automatically created).

    Returns:
        On success — dict with keys:
          artifact_name   — name searched for
          artifact_id     — numeric GitHub artifact ID
          run_id          — the run ID used
          output_dir      — absolute path of the extraction directory
          files           — list of relative paths inside the extracted archive
          total_files     — number of extracted files
          trace_zips      — list of *-trace.zip paths found (for Detective)
          junit_xml       — path to e2e-junit.xml if present (else empty string)
        On failure — dict with keys:
          error                — human-readable error message
          available_artifacts  — list of artifact names that do exist (when not found)
    """
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        return {"error": "GITHUB_TOKEN is not set — cannot download CI artifacts."}

    owner = os.getenv("AUT_GITHUB_OWNER", "lokeshsharma99")
    repo = os.getenv("AUT_GITHUB_REPO", "GDS-Demo-App")
    run_id = str(run_id).strip()

    # Step 1 — list artifacts for this run
    list_url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
    try:
        artifacts_data = json.loads(_github_get(list_url, token))
    except Exception as exc:
        return {"error": f"Failed to list artifacts for run {run_id}: {exc}"}

    # Step 2 — locate the requested artifact
    artifact = next(
        (a for a in artifacts_data.get("artifacts", []) if a["name"] == artifact_name),
        None,
    )
    if artifact is None:
        available = [a["name"] for a in artifacts_data.get("artifacts", [])]
        return {
            "error": (
                f"Artifact '{artifact_name}' not found in run {run_id}. "
                f"Note: 'playwright-traces' is only uploaded when E2E tests fail."
            ),
            "available_artifacts": available,
            "run_id": run_id,
        }

    if artifact.get("expired"):
        return {
            "error": f"Artifact '{artifact_name}' has expired (retention period exceeded).",
            "run_id": run_id,
        }

    # Step 3 — download the outer artifact ZIP via REST API
    art_id = artifact["id"]
    download_url = (
        f"https://api.github.com/repos/{owner}/{repo}/actions/artifacts/{art_id}/zip"
    )
    dest = Path(output_dir) if output_dir else Path(
        tempfile.mkdtemp(prefix=f"qap_{run_id}_{artifact_name}_")
    )
    dest.mkdir(parents=True, exist_ok=True)
    zip_path = dest / f"_download_{artifact_name}.zip"

    try:
        zip_bytes = _github_get(download_url, token)
        zip_path.write_bytes(zip_bytes)
    except Exception as exc:
        return {"error": f"Failed to download artifact (id={art_id}): {exc}", "run_id": run_id}

    # Step 4 — extract
    import zipfile as _zf

    try:
        with _zf.ZipFile(zip_path, "r") as zf:
            zf.extractall(dest)
            extracted_files = zf.namelist()
        zip_path.unlink()
    except _zf.BadZipFile as exc:
        return {"error": f"Artifact ZIP is corrupt: {exc}", "run_id": run_id}

    # Step 5 — locate useful files inside the extraction
    #
    # Playwright trace file naming inside a playwright-traces artifact:
    #   actions/upload-artifact uploads `path: test-results/` so the ZIP entries
    #   are relative to that dir.  Each failing test gets its own subdirectory:
    #     FR-02-01-Submit-form-chromium/trace.zip
    #     FR-02-01-Submit-form-chromium/screenshot.png
    #   The trace files are always named exactly `trace.zip`, so we match on
    #   the final path component, not a suffix like "-trace.zip".
    trace_zips = [
        str((dest / f).resolve())
        for f in extracted_files
        if f == "trace.zip" or f.endswith("/trace.zip")
    ]
    # Prefer e2e-junit.xml specifically; fall back to any .xml in the archive.
    junit_xml = next(
        (str((dest / f).resolve()) for f in extracted_files if f == "e2e-junit.xml"),
        next(
            (str((dest / f).resolve()) for f in extracted_files if f.endswith(".xml")),
            "",
        ),
    )

    return {
        "artifact_name": artifact_name,
        "artifact_id": art_id,
        "run_id": run_id,
        "output_dir": str(dest.resolve()),
        "files": extracted_files,
        "total_files": len(extracted_files),
        "trace_zips": trace_zips,
        "junit_xml": junit_xml,
    }


# ---------------------------------------------------------------------------
# Tool 2 — parse_junit_xml
# ---------------------------------------------------------------------------

def parse_junit_xml(xml_path: str) -> dict:
    """Parse a Playwright JUnit XML results file for exact failure details.

    Playwright's `junit` reporter writes `e2e-junit.xml` inside the
    `playwright-traces` artifact.  This file contains the verbatim error message
    and full stack trace for every failing test — information that is NOT reliably
    extractable from raw CI job logs.

    JUnit XML structure produced by Playwright
    ------------------------------------------
    <testsuites>
      <testsuite name="Functional Regression" tests="N" failures="N" time="...">
        <testcase name="FR-02-01: ..." classname="automation/features/..." time="...">
          <failure message="Error: locator('...') timed out after 30000ms">
            TimeoutError: locator('...') timed out after 30000ms
                at Object.<anonymous> (.../pages/MyPage.ts:42:18)
                ...
          </failure>
        </testcase>
      </testsuite>
    </testsuites>

    Args:
        xml_path: Absolute path to the JUnit XML file (e.g. from download_ci_artifact).

    Returns:
        On success — dict with keys:
          total_tests  — total test case count
          passed       — passing tests
          failed       — failing tests (failure + error elements)
          skipped      — skipped tests
          failures     — list of dicts: {test_name, suite, class, error_message,
                         stack_trace, duration_s}
          suites       — list of suite-level summaries
        On failure — dict with key: error
    """
    path = Path(xml_path)
    if not path.exists():
        return {"error": f"JUnit XML file not found: {xml_path}"}

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return {"error": f"XML parse error: {exc}"}

    suites = (
        list(root.findall("testsuite"))
        if root.tag == "testsuites"
        else ([root] if root.tag == "testsuite" else [])
    )
    if not suites:
        return {"error": f"No <testsuite> elements found in {xml_path}"}

    total = failed = skipped = 0
    failures: list[dict] = []
    suite_summaries: list[dict] = []

    for suite in suites:
        s_tests = int(suite.get("tests", 0))
        s_fail = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
        s_skip = int(suite.get("skipped", 0))
        total += s_tests
        failed += s_fail
        skipped += s_skip

        suite_summaries.append({
            "name": suite.get("name", ""),
            "tests": s_tests,
            "failures": s_fail,
            "skipped": s_skip,
            "time": suite.get("time", "0"),
        })

        for tc in suite.findall("testcase"):
            # NOTE: Do NOT use `tc.find("failure") or tc.find("error")` — Python
            # evaluates XML Elements in boolean context as False when they have no
            # children/text, causing the `or` to incorrectly fall through.
            fail_el = tc.find("failure")
            if fail_el is None:
                fail_el = tc.find("error")
            if fail_el is None:
                continue
            failures.append({
                "test_name": tc.get("name", ""),
                "suite": suite.get("name", ""),
                "class": tc.get("classname", ""),
                "error_message": (fail_el.get("message") or "").strip(),
                "stack_trace": (fail_el.text or "").strip(),
                "duration_s": tc.get("time", "0"),
            })

    return {
        "total_tests": total,
        "passed": total - failed - skipped,
        "failed": failed,
        "skipped": skipped,
        "failures": failures,
        "suites": suite_summaries,
    }


# ---------------------------------------------------------------------------
# Tool 3 — parse_allure_results
# ---------------------------------------------------------------------------

def parse_allure_results(results_dir: str) -> dict:
    """Parse Allure result JSON files to extract structured test outcomes.

    The `allure-results` artifact contains one `*-result.json` per test case.
    For failing tests, `statusDetails.message` holds the verbatim error message
    and `statusDetails.trace` holds the full stack trace.

    This artifact is ALWAYS uploaded (not just on failure), so it can also be
    used to verify that all tests passed when `playwright-traces` is absent.

    Allure result JSON schema (relevant fields)
    -------------------------------------------
    {
      "name": "FR-02-08: Filling all fields and clicking Continue moves to Step 2",
      "status": "passed" | "failed" | "broken" | "skipped",
      "statusDetails": {
        "message": "Error: ...",   ← verbatim error (present on failed/broken)
        "trace": "..."             ← full stack trace
      },
      "labels": [
        {"name": "feature", "value": "..."},
        {"name": "story", "value": "..."},
        {"name": "tag", "value": "..."}
      ],
      "parameters": [{"name": "...", "value": "..."}],
      "start": 1714298400000,
      "stop": 1714298412000
    }

    Args:
        results_dir: Path to the extracted allure-results directory.

    Returns:
        On success — dict with keys:
          total_tests  — total result count
          passed       — count
          failed       — count (assertion failures)
          broken       — count (infra / uncaught exceptions)
          skipped      — count
          failures     — list of dicts for failed + broken: {name, status, feature,
                         story, error_message, stack_trace, parameters, duration_ms}
        On failure — dict with key: error
    """
    rdir = Path(results_dir)
    if not rdir.exists():
        return {"error": f"Results directory not found: {results_dir}"}

    result_files = list(rdir.glob("*-result.json"))
    if not result_files:
        return {"error": f"No *-result.json files found in: {results_dir}"}

    counts: dict[str, int] = {"passed": 0, "failed": 0, "broken": 0, "skipped": 0}
    failures: list[dict] = []

    for rf in result_files:
        try:
            data: dict = json.loads(rf.read_text(encoding="utf-8"))
        except Exception:
            continue

        status = data.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1

        if status in ("failed", "broken"):
            details = data.get("statusDetails") or {}
            labels = {
                lb["name"]: lb["value"]
                for lb in (data.get("labels") or [])
                if "name" in lb and "value" in lb
            }
            start = data.get("start") or 0
            stop = data.get("stop") or 0
            failures.append({
                "name": data.get("name", "unknown"),
                "status": status,
                "feature": labels.get("feature", ""),
                "story": labels.get("story", ""),
                "error_message": details.get("message", "").strip(),
                "stack_trace": details.get("trace", "").strip(),
                "parameters": [
                    p.get("value", "") for p in (data.get("parameters") or [])
                ],
                "duration_ms": stop - start,
            })

    return {
        "total_tests": sum(counts.values()),
        "passed": counts.get("passed", 0),
        "failed": counts.get("failed", 0),
        "broken": counts.get("broken", 0),
        "skipped": counts.get("skipped", 0),
        "failures": failures,
    }
