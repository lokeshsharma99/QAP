"""
Observability Agent Tools
=========================

Tools for inspecting Azure Container Apps health, logs, DB connectivity,
and API responsiveness. All tools use the Azure CLI (az) subprocess calls
so they work both locally (with az login) and in ACA with managed identity.
"""

import json
import os
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone


def _run_az(*args: str) -> tuple[int, str, str]:
    """Run an `az` CLI command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        ["az", *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


# ---------------------------------------------------------------------------
# Tool: check_api_health
# ---------------------------------------------------------------------------
def check_api_health(url: str | None = None) -> str:
    """
    Probe the Quality Autopilot API /health endpoint.

    Args:
        url: Override the API base URL. Defaults to ACA_API_URL env var or the
             production FQDN. Do not include /health suffix.

    Returns:
        JSON-serialisable string describing the health check result.
    """
    base = (
        url
        or os.getenv("ACA_API_URL")
        or "https://qap-dev-api.nicesand-63588b93.uksouth.azurecontainerapps.io"
    ).rstrip("/")
    target = f"{base}/health"
    try:
        req = urllib.request.Request(target, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read(4096).decode("utf-8", errors="replace")
            return json.dumps({
                "url": target,
                "status_code": resp.status,
                "body": body[:500],
                "healthy": resp.status == 200,
            })
    except urllib.error.HTTPError as e:
        return json.dumps({"url": target, "status_code": e.code, "error": str(e), "healthy": False})
    except Exception as e:
        return json.dumps({"url": target, "status_code": None, "error": str(e), "healthy": False})


# ---------------------------------------------------------------------------
# Tool: get_aca_revision_status
# ---------------------------------------------------------------------------
def get_aca_revision_status(
    app_name: str = "qap-dev-api",
    resource_group: str = "rg-quality-autopilot",
) -> str:
    """
    List ACA revisions for a container app and their running state.

    Args:
        app_name: The ACA container app name (default: qap-dev-api).
        resource_group: Azure resource group name (default: rg-quality-autopilot).

    Returns:
        JSON string with list of revisions: name, runningState, createdTime, trafficWeight.
    """
    rc, out, err = _run_az(
        "containerapp", "revision", "list",
        "--name", app_name,
        "--resource-group", resource_group,
        "--query", "[].{name:name, state:properties.runningState, created:properties.createdTime, traffic:properties.trafficWeight}",
        "-o", "json",
    )
    if rc != 0:
        return json.dumps({"error": err or "az cli failed", "returncode": rc})
    try:
        return out
    except Exception as e:
        return json.dumps({"error": str(e), "raw": out[:500]})


# ---------------------------------------------------------------------------
# Tool: get_aca_logs
# ---------------------------------------------------------------------------
def get_aca_logs(
    app_name: str = "qap-dev-api",
    resource_group: str = "rg-quality-autopilot",
    lines: int = 50,
    revision: str | None = None,
) -> str:
    """
    Fetch recent log lines from an ACA container app via az containerapp logs show.

    Args:
        app_name: ACA container app name (default: qap-dev-api).
        resource_group: Azure resource group (default: rg-quality-autopilot).
        lines: Number of recent log lines to fetch (default: 50, max 200).
        revision: Specific revision name to target. If None, uses the active revision.

    Returns:
        Raw log text (last N lines) or an error description.
    """
    lines = min(int(lines), 200)
    cmd = [
        "containerapp", "logs", "show",
        "--name", app_name,
        "--resource-group", resource_group,
        "--tail", str(lines),
        "--type", "console",
    ]
    if revision:
        cmd += ["--revision", revision]

    rc, out, err = _run_az(*cmd)
    if rc != 0:
        return f"ERROR fetching logs (rc={rc}): {err or 'unknown az error'}"
    return out or "(no log output returned)"


# ---------------------------------------------------------------------------
# Tool: get_aca_env_vars
# ---------------------------------------------------------------------------
def get_aca_env_vars(
    app_name: str = "qap-dev-api",
    resource_group: str = "rg-quality-autopilot",
    filter_prefix: str | None = None,
) -> str:
    """
    List environment variable names (not values) set on an ACA container app.
    Useful to check if DB_HOST, EMBEDDING_PROVIDER, etc. are configured.

    Args:
        app_name: ACA container app name.
        resource_group: Azure resource group.
        filter_prefix: Optional prefix to filter env var names (e.g. "DB_", "AZURE_").

    Returns:
        JSON list of env var names (values are hidden for security).
    """
    rc, out, err = _run_az(
        "containerapp", "show",
        "--name", app_name,
        "--resource-group", resource_group,
        "--query",
        "properties.template.containers[0].env[].name",
        "-o", "json",
    )
    if rc != 0:
        return json.dumps({"error": err or "az cli failed", "returncode": rc})
    try:
        names: list[str] = json.loads(out) if out else []
        if filter_prefix:
            names = [n for n in names if n.startswith(filter_prefix)]
        return json.dumps({"count": len(names), "env_var_names": sorted(names)})
    except Exception as e:
        return json.dumps({"error": str(e), "raw": out[:500]})


# ---------------------------------------------------------------------------
# Tool: run_db_check
# ---------------------------------------------------------------------------
def run_db_check(
    app_name: str = "qap-dev-api",
    resource_group: str = "rg-quality-autopilot",
) -> str:
    """
    Inspect ACA logs for DB connectivity errors (localhost, connection refused,
    psycopg errors). Reports any DB_HOST issues found.

    Args:
        app_name: ACA container app name.
        resource_group: Azure resource group.

    Returns:
        JSON with db_issues list and db_host_configured bool.
    """
    rc, out, err = _run_az(
        "containerapp", "logs", "show",
        "--name", app_name,
        "--resource-group", resource_group,
        "--tail", "100",
        "--type", "console",
    )
    raw_logs = out if rc == 0 else ""

    db_error_patterns = [
        "localhost:5432",
        "connection refused",
        "psycopg",
        "could not connect",
        "OperationalError",
        "DB_HOST",
        "sqlalchemy.exc",
    ]

    found_issues: list[str] = []
    for line in raw_logs.splitlines():
        lower = line.lower()
        for pattern in db_error_patterns:
            if pattern.lower() in lower:
                found_issues.append(line.strip()[:200])
                break

    # Check if DB_HOST env var is set
    rc2, out2, _ = _run_az(
        "containerapp", "show",
        "--name", app_name,
        "--resource-group", resource_group,
        "--query",
        "properties.template.containers[0].env[?name=='DB_HOST'].value | [0]",
        "-o", "tsv",
    )
    db_host_configured = bool(out2.strip() and out2.strip() != "None")

    return json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_host_configured": db_host_configured,
        "db_host_value_masked": "***" if db_host_configured else "(not set)",
        "db_error_count": len(found_issues),
        "db_issues": found_issues[:10],
        "log_fetch_error": err if rc != 0 else None,
    })
