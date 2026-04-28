"""
Detective Agent Tools
======================

Trace parsing and log analysis tools for the Detective Agent.

Playwright trace.zip internal structure
----------------------------------------
A trace produced by `playwright test --trace on` is a ZIP containing:

  trace.trace          — newline-delimited JSON (NDJSON); one event per line.
                         Event types relevant to failure analysis:
                           context-options    — browser / viewport config
                           screencast-frame   — base64 PNG frame at a timestamp
                           before             — action about to start (type, selector, value)
                           input              — keyboard/mouse input detail
                           after              — action result; contains error if it threw
                           event              — console log, page error, network request
                           resource-snapshot  — full DOM snapshot for a frame
                           log                — string message attached to an action

  *.network            — newline-delimited JSON of network requests/responses.
                         Fields: url, method, status, headers, timing, failure.

  resources/           — binary blobs: screenshots (*.png / base64 in events),
                         DOM snapshots, fonts, images used in snapshots.

  trace.stacks         — JSON mapping callId → source location (file:line:col).
"""

import json
import re
import zipfile
from pathlib import Path


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _read_ndjson(raw: str) -> list[dict]:
    """Parse newline-delimited JSON, skipping malformed lines."""
    events = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return events


def _ms_to_s(ms: float | None) -> str:
    if ms is None:
        return "?"
    return f"{ms / 1000:.3f}s"


def _extract_selector(action: dict) -> str | None:
    """Pull the selector string out of an action event in multiple trace formats."""
    # Newer format stores params.selector or params.locator
    params = action.get("params") or {}
    sel = params.get("selector") or params.get("locator")
    if sel:
        return sel
    # Older format has a direct 'selector' key on the action
    return action.get("selector")


def _extract_error(after_event: dict) -> str | None:
    """Extract the error message from an 'after' event."""
    error = after_event.get("error")
    if not error:
        return None
    if isinstance(error, str):
        return error
    if isinstance(error, dict):
        msg = error.get("message") or error.get("value") or ""
        stack = error.get("stack") or ""
        return f"{msg}\n{stack}".strip() if stack else msg
    return None


def _classify_error(error_msg: str, selector: str | None, timeout: bool) -> str:
    """Map a raw error message to a Detective classification."""
    if not error_msg:
        return "UNKNOWN"
    e = error_msg.lower()
    if any(k in e for k in ("econnrefused", "net::err", "503", "502", "504", "connection reset", "socket hang up")):
        return "ENV_FAILURE"
    if any(k in e for k in ("waiting for locator", "locator.click", "locator.fill", "element is not attached",
                             "strict mode violation", "resolved to", "expected to be visible",
                             "getbytestid", "getbyrole", "getbytext", "locator(",)):
        return "LOCATOR_STALE"
    if timeout and selector:
        return "LOCATOR_STALE"
    if timeout and not selector:
        return "TIMING_FLAKE"
    if any(k in e for k in ("tobe", "toequal", "tocontain", "tohavetext", "tohavevalue",
                             "expect(", "received", "expected value")):
        return "LOGIC_CHANGE"
    if any(k in e for k in ("unique constraint", "duplicate key", "foreign key", "not found in db",
                             "invalid credentials", "user already exists")):
        return "DATA_MISMATCH"
    if selector:
        return "LOCATOR_STALE"
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Public tools
# ---------------------------------------------------------------------------

def parse_trace_zip(trace_path: str) -> dict:
    """Parse a Playwright trace.zip and return a structured analysis dict.

    Extracts the action timeline, the exact failure point with error message,
    network requests, console errors, and a preliminary classification.

    Args:
        trace_path: Absolute or relative path to the Playwright trace.zip file.

    Returns:
        A dict with keys:
          trace_file       — filename parsed
          playwright_version — detected version (if present in context-options)
          test_title       — title from context-options (if present)
          total_actions    — count of recorded actions
          action_timeline  — list of action summaries (step, type, selector, duration, status)
          failure_action   — dict describing the first action that threw an error
          error_message    — verbatim error string from the failing action
          error_type       — LOCATOR_STALE | TIMING_FLAKE | LOGIC_CHANGE | ENV_FAILURE |
                             DATA_MISMATCH | UNKNOWN
          failed_selector  — the selector/locator string that failed (if any)
          timeout_detected — bool
          console_errors   — list of browser console error messages
          page_errors      — list of uncaught page errors
          network_failures — list of failed HTTP requests (4xx/5xx/aborted)
          slow_requests    — list of requests > 2 s
          screenshots      — list of screenshot resource names found in the archive
          call_stacks      — list of {callId, location} from trace.stacks
          raw_error        — dict: error object verbatim from the failing after-event
          summary          — plain-English paragraph summarising the failure
    """
    path = Path(trace_path)
    if not path.exists():
        return {"error": f"Trace file not found: {trace_path}"}
    if path.suffix.lower() != ".zip":
        return {"error": f"Expected a .zip file, got: {trace_path}"}

    try:
        with zipfile.ZipFile(path, "r") as zf:
            file_list = zf.namelist()

            # ----------------------------------------------------------------
            # 1. Read trace events (*.trace files — NDJSON)
            # ----------------------------------------------------------------
            trace_files = [f for f in file_list if f.endswith(".trace")]
            all_events: list[dict] = []
            for tf in trace_files:
                raw = zf.read(tf).decode("utf-8", errors="replace")
                all_events.extend(_read_ndjson(raw))

            # ----------------------------------------------------------------
            # 2. Read network log (*.network files — NDJSON)
            # ----------------------------------------------------------------
            network_events: list[dict] = []
            for nf in [f for f in file_list if f.endswith(".network")]:
                raw = zf.read(nf).decode("utf-8", errors="replace")
                network_events.extend(_read_ndjson(raw))

            # ----------------------------------------------------------------
            # 3. Read call stacks (trace.stacks — JSON object)
            # ----------------------------------------------------------------
            call_stacks: list[dict] = []
            if "trace.stacks" in file_list:
                try:
                    stacks_raw = zf.read("trace.stacks").decode("utf-8", errors="replace")
                    stacks_obj = json.loads(stacks_raw)
                    if isinstance(stacks_obj, dict):
                        for call_id, frames in stacks_obj.items():
                            if frames:
                                call_stacks.append({"callId": call_id, "location": frames[0]})
                except Exception:
                    pass

            # ----------------------------------------------------------------
            # 4. Collect screenshot resource names
            # ----------------------------------------------------------------
            screenshots = [f for f in file_list if re.search(r"\.(png|jpeg|jpg)$", f, re.IGNORECASE)]

    except zipfile.BadZipFile:
        return {"error": f"Invalid or corrupt zip file: {trace_path}"}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}

    # -------------------------------------------------------------------------
    # 5. Parse context-options event (test metadata)
    # -------------------------------------------------------------------------
    playwright_version = None
    test_title = None
    for ev in all_events:
        if ev.get("type") == "context-options":
            playwright_version = ev.get("sdkLanguage") or ev.get("version")
            test_title = ev.get("title") or ev.get("testId")
            break

    # -------------------------------------------------------------------------
    # 6. Build action timeline from before/after pairs
    # -------------------------------------------------------------------------
    # Collect 'before' events indexed by callId
    before_map: dict[str, dict] = {}
    for ev in all_events:
        if ev.get("type") == "before":
            cid = ev.get("callId") or ev.get("id") or str(id(ev))
            before_map[cid] = ev

    action_timeline: list[dict] = []
    failure_action: dict | None = None
    error_message: str | None = None
    failed_selector: str | None = None
    timeout_detected = False
    raw_error: dict | None = None

    for ev in all_events:
        if ev.get("type") != "after":
            continue

        cid = ev.get("callId") or ev.get("id") or ""
        before = before_map.get(cid, {})

        action_type = before.get("apiName") or before.get("method") or ev.get("apiName") or "unknown"
        selector = _extract_selector(before) or _extract_selector(ev)
        start_time = before.get("startTime") or before.get("wallTime")
        end_time = ev.get("endTime") or ev.get("wallTime")
        duration_ms: float | None = None
        if start_time and end_time:
            try:
                duration_ms = float(end_time) - float(start_time)
            except (TypeError, ValueError):
                pass

        err = _extract_error(ev)
        status = "error" if err else "ok"

        entry = {
            "step": len(action_timeline) + 1,
            "type": action_type,
            "selector": selector,
            "duration": _ms_to_s(duration_ms),
            "status": status,
            "error": err,
        }
        action_timeline.append(entry)

        if err and failure_action is None:
            failure_action = entry
            error_message = err
            failed_selector = selector
            raw_error = ev.get("error")
            if "timeout" in err.lower() or "timed out" in err.lower():
                timeout_detected = True

    # Also catch timeout from log events
    if not timeout_detected:
        for ev in all_events:
            if ev.get("type") == "log":
                msg = str(ev.get("message") or "")
                if "timeout" in msg.lower():
                    timeout_detected = True
                    break

    # -------------------------------------------------------------------------
    # 7. Classify the error
    # -------------------------------------------------------------------------
    error_type = _classify_error(error_message or "", failed_selector, timeout_detected)

    # -------------------------------------------------------------------------
    # 8. Console errors and page errors
    # -------------------------------------------------------------------------
    console_errors: list[str] = []
    page_errors: list[str] = []
    for ev in all_events:
        ev_type = ev.get("type")
        if ev_type == "event":
            inner = ev.get("event") or {}
            inner_type = inner.get("type") or ""
            if inner_type == "console":
                # console entries from browser
                for entry in (inner.get("messages") or []):
                    if isinstance(entry, dict) and entry.get("type") == "error":
                        console_errors.append(entry.get("text") or "")
            elif inner_type == "pageError":
                page_errors.append(str(inner.get("error") or inner.get("message") or ""))
        elif ev_type == "console" and ev.get("messageType") == "error":
            console_errors.append(ev.get("text") or "")
        elif ev_type == "pageError":
            page_errors.append(str(ev.get("error") or ev.get("message") or ""))

    # -------------------------------------------------------------------------
    # 9. Network analysis
    # -------------------------------------------------------------------------
    network_failures: list[dict] = []
    slow_requests: list[dict] = []

    for req in network_events:
        url = req.get("url") or ""
        method = req.get("method") or "GET"
        status = req.get("status")
        failure = req.get("failure") or req.get("failureText")
        timing = req.get("timing") or {}
        duration_ms_net = timing.get("responseEnd", 0) - timing.get("requestTime", 0) * 1000 \
            if "requestTime" in timing else None

        if failure or (status and int(status) >= 400):
            network_failures.append({
                "url": url,
                "method": method,
                "status": status,
                "failure": failure,
            })

        if duration_ms_net and duration_ms_net > 2000:
            slow_requests.append({
                "url": url,
                "method": method,
                "duration": _ms_to_s(duration_ms_net),
                "status": status,
            })

    # -------------------------------------------------------------------------
    # 10. Build plain-English summary
    # -------------------------------------------------------------------------
    if failure_action:
        sel_str = f" on selector `{failed_selector}`" if failed_selector else ""
        timeout_str = " (timeout)" if timeout_detected else ""
        summary = (
            f"Test failed at step {failure_action['step']} — "
            f"action `{failure_action['type']}`{sel_str}{timeout_str}. "
            f"Error: {(error_message or '')[:300]}. "
            f"Classification: {error_type}. "
            f"Total actions recorded: {len(action_timeline)}. "
        )
        if network_failures:
            summary += f"Network failures detected: {len(network_failures)} request(s). "
        if console_errors:
            summary += f"Browser console errors: {len(console_errors)}. "
    else:
        summary = (
            f"No action-level error found in trace. "
            f"Total actions: {len(action_timeline)}. "
            f"Network failures: {len(network_failures)}. "
            f"Console errors: {len(console_errors)}. "
            f"Page errors: {len(page_errors)}."
        )

    return {
        "trace_file": path.name,
        "playwright_version": playwright_version,
        "test_title": test_title,
        "total_actions": len(action_timeline),
        "action_timeline": action_timeline,
        "failure_action": failure_action,
        "error_message": error_message,
        "error_type": error_type,
        "failed_selector": failed_selector,
        "timeout_detected": timeout_detected,
        "console_errors": console_errors[:20],
        "page_errors": page_errors[:10],
        "network_failures": network_failures[:20],
        "slow_requests": slow_requests[:10],
        "screenshots": screenshots,
        "call_stacks": call_stacks[:10],
        "raw_error": raw_error,
        "summary": summary,
    }


def extract_screenshot_from_trace(trace_path: str, output_dir: str = ".") -> dict:
    """Extract all screenshots embedded in a Playwright trace.zip to disk.

    Playwright embeds PNG screenshots as binary blobs inside the
    resources/ folder of the trace archive.  This tool extracts them
    so the Detective (or a human) can visually inspect the state of the
    page at the moment of failure.

    Args:
        trace_path: Path to the Playwright trace.zip file.
        output_dir: Directory to write the extracted PNG files into.
                    Defaults to the current working directory.

    Returns:
        A dict with:
          extracted     — list of absolute paths to the written PNG files
          count         — number of screenshots extracted
          output_dir    — the directory they were written to
          error         — error message if extraction failed (key absent on success)
    """
    path = Path(trace_path)
    out = Path(output_dir)
    if not path.exists():
        return {"error": f"Trace file not found: {trace_path}", "count": 0, "extracted": []}

    try:
        out.mkdir(parents=True, exist_ok=True)
        extracted: list[str] = []

        with zipfile.ZipFile(path, "r") as zf:
            for name in zf.namelist():
                if re.search(r"\.(png|jpeg|jpg)$", name, re.IGNORECASE):
                    # Flatten path — write as <trace_stem>_<basename>
                    safe_name = re.sub(r"[/\\]", "_", name)
                    dest = out / f"{path.stem}_{safe_name}"
                    dest.write_bytes(zf.read(name))
                    extracted.append(str(dest.resolve()))

        return {
            "extracted": extracted,
            "count": len(extracted),
            "output_dir": str(out.resolve()),
        }
    except zipfile.BadZipFile:
        return {"error": f"Invalid or corrupt zip file: {trace_path}", "count": 0, "extracted": []}
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "count": 0, "extracted": []}


def parse_ci_log(log_content: str) -> dict:
    """Parse CI/CD log output to extract failure signals.

    Understands GitHub Actions, Azure Pipelines, and plain Playwright/
    Cucumber terminal output.  Extracts structured signals the Detective
    can reason over instead of raw text.

    Args:
        log_content: Raw CI/CD log text.

    Returns:
        A dict with:
          error_lines        — up to 20 lines that look like errors
          timeout_detected   — bool
          selector_errors    — lines mentioning locator / selector failures
          assertion_errors   — lines mentioning expect / assert failures
          env_errors         — lines indicating infrastructure issues
          test_results       — parsed Cucumber/Playwright result lines (pass/fail/skip)
          failed_test_names  — list of test titles extracted from failure lines
          total_lines        — total line count in the log
          classification     — preliminary heuristic classification
    """
    lines = log_content.split("\n")

    error_lines = [ln for ln in lines if re.search(r"error|FAIL|✘|×", ln, re.IGNORECASE)]
    timeout_detected = any(re.search(r"timeout|timed out", ln, re.IGNORECASE) for ln in lines)

    selector_errors = [
        ln for ln in lines
        if re.search(r"locator\(|getByTestId|getByRole|getByText|getByLabel|"
                     r"not found|not visible|not attached|strict mode violation", ln, re.IGNORECASE)
    ]
    assertion_errors = [
        ln for ln in lines
        if re.search(r"expect\(|toHaveText|toBeVisible|toBe\(|toEqual|toContain|"
                     r"Expected:|Received:|AssertionError", ln, re.IGNORECASE)
    ]
    env_errors = [
        ln for ln in lines
        if re.search(r"ECONNREFUSED|ENOTFOUND|ETIMEDOUT|503|502|504|"
                     r"connection reset|socket hang up|net::ERR", ln, re.IGNORECASE)
    ]

    # Extract test names from Playwright / Cucumber output
    # Playwright:  "  1) [chromium] › login.spec.ts:15:5 › Login › valid login"
    # Cucumber:    "  ✘ Scenario: User can log in with valid credentials"
    failed_test_names: list[str] = []
    test_results: list[dict] = []

    for ln in lines:
        # Playwright failed test line
        m = re.match(r"\s+\d+\)\s+\[?\w+\]?\s*›?\s*(.+)", ln)
        if m and re.search(r"fail|error|✘|×", ln, re.IGNORECASE):
            failed_test_names.append(m.group(1).strip())

        # Cucumber scenario result
        m2 = re.match(r"\s*(✔|✘|[-])\s+(Scenario|Feature|Step):\s*(.+)", ln)
        if m2:
            test_results.append({
                "status": "pass" if m2.group(1) == "✔" else ("skip" if m2.group(1) == "-" else "fail"),
                "type": m2.group(2),
                "name": m2.group(3).strip(),
            })

        # Generic "FAILED" line
        m3 = re.search(r"FAILED\s+(.+)", ln)
        if m3:
            name = m3.group(1).strip()
            if name not in failed_test_names:
                failed_test_names.append(name)

    # Heuristic classification
    classification = classify_failure({
        "env_errors": env_errors,
        "selector_errors": selector_errors,
        "assertion_errors": assertion_errors,
        "timeout_detected": timeout_detected,
    })

    return {
        "error_lines": error_lines[:20],
        "timeout_detected": timeout_detected,
        "selector_errors": selector_errors[:10],
        "assertion_errors": assertion_errors[:10],
        "env_errors": env_errors[:10],
        "test_results": test_results[:50],
        "failed_test_names": failed_test_names[:20],
        "total_lines": len(lines),
        "classification": classification,
    }


def classify_failure(parsed_log: dict) -> str:
    """Classify a failure from parsed log signals.

    Applies a priority-ordered decision tree:
      ENV_FAILURE    — infrastructure signals first (highest confidence)
      LOCATOR_STALE  — selector errors without ambiguous assertion failures
      TIMING_FLAKE   — timeout without any selector signal
      LOGIC_CHANGE   — assertion failure without selector involvement
      DATA_MISMATCH  — selector + assertion (data rendered differently than expected)
      UNKNOWN        — insufficient signals

    Args:
        parsed_log: Output from parse_ci_log() or parse_trace_zip().

    Returns:
        Classification string.
    """
    if parsed_log.get("env_errors"):
        return "ENV_FAILURE"
    has_selector = bool(parsed_log.get("selector_errors") or parsed_log.get("failed_selector"))
    has_assertion = bool(parsed_log.get("assertion_errors"))
    timeout = bool(parsed_log.get("timeout_detected"))

    if has_selector and not has_assertion:
        return "LOCATOR_STALE"
    if timeout and not has_selector:
        return "TIMING_FLAKE"
    if has_assertion and not has_selector:
        return "LOGIC_CHANGE"
    if has_selector and has_assertion:
        return "DATA_MISMATCH"
    return "UNKNOWN"
