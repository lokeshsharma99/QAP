"""
RTM (Requirements Traceability Matrix) API
===========================================

REST endpoints that let users, agents, and the Control Plane query the full
traceability chain:

    Jira Story → Acceptance Criterion → Gherkin Scenario
              → Step Def → Page Object → AUT Element

Routes:
    GET  /rtm                   — full RTM listing (optionally filtered by ticket)
    GET  /rtm/search            — semantic search across RTM rows
    GET  /rtm/ticket/{key}      — all scenarios covering a specific ticket
    POST /rtm/explain           — natural-language explanation of a scenario's lineage
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/rtm", tags=["rtm"])

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_AUTOMATION_DIR = _PROJECT_ROOT / "automation"
_FEATURES_DIR = _AUTOMATION_DIR / "features"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_feature_files() -> list[dict]:
    """Scan automation/features/ and parse every .feature file into RTM rows.

    Returns one row per Scenario:
    {
        "ticket_ids": [...],
        "feature_title": "...",
        "feature_file": "automation/features/foo.feature",
        "scenario_name": "...",
        "tags": [...],
        "scenario_type": "Scenario|Scenario Outline",
        "steps": [...],
    }
    """
    rows: list[dict] = []
    ticket_re = re.compile(r"@([A-Z][A-Z0-9]+-\d+)", re.IGNORECASE)
    tag_re    = re.compile(r"@(\w[\w-]*)")
    feature_re = re.compile(r"^\s*Feature\s*:\s*(.+)", re.MULTILINE)
    scenario_re = re.compile(r"^\s*(Scenario(?:\s+Outline)?)\s*:\s*(.+)", re.MULTILINE)
    step_re = re.compile(r"^\s*(Given|When|Then|And|But)\s+(.+)", re.MULTILINE)

    if not _FEATURES_DIR.exists():
        return rows

    for feature_path in _FEATURES_DIR.rglob("*.feature"):
        try:
            content = feature_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        feature_m = feature_re.search(content)
        feature_title = feature_m.group(1).strip() if feature_m else feature_path.stem

        # Collect all @-tags that appear before any Scenario
        feature_level_tags = tag_re.findall(content.split("Scenario")[0]) if "Scenario" in content else []
        ticket_ids = list(dict.fromkeys(ticket_re.findall(content)))

        # Split on Scenario boundaries to get per-scenario text
        parts = re.split(r"(?=\s*Scenario(?:\s+Outline)?:)", content)

        for part in parts:
            sm = scenario_re.search(part)
            if not sm:
                continue
            scenario_type = sm.group(1).strip()
            scenario_name = sm.group(2).strip()
            scenario_tags = list(dict.fromkeys(tag_re.findall(part.split(sm.group(0))[0])))
            all_tags = list(dict.fromkeys(feature_level_tags + scenario_tags))
            scenario_ticket_ids = list(dict.fromkeys(
                ticket_re.findall(part.split(sm.group(0))[0]) + ticket_ids
            ))
            steps = [f"{s.group(1)} {s.group(2).strip()}" for s in step_re.finditer(part)]

            rel_path = str(feature_path.relative_to(_PROJECT_ROOT)).replace("\\", "/")
            rows.append({
                "ticket_ids": scenario_ticket_ids,
                "feature_title": feature_title,
                "feature_file": rel_path,
                "scenario_name": scenario_name,
                "scenario_type": scenario_type,
                "tags": all_tags,
                "steps": steps,
            })

    return rows


def _query_rtm_kb(query: str, num_results: int = 20) -> list[dict]:
    """Query the RTM PgVector KB with a semantic search string."""
    try:
        from db.session import get_rtm_kb
        rtm_kb = get_rtm_kb()
        results = rtm_kb.search(query=query, num_documents=num_results)
        rows: list[dict] = []
        for doc in results:
            meta = doc.meta_data or {}
            rows.append({
                "ticket_id": meta.get("ticket_id", ""),
                "ac_id": meta.get("ac_id", ""),
                "scenario_name": meta.get("scenario_name", ""),
                "feature_file": meta.get("feature_file", ""),
                "feature_title": meta.get("feature_title", ""),
                "tags": meta.get("tags", ""),
                "source": "rtm_kb",
                "content": doc.content,
            })
        return rows
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class RTMRow(BaseModel):
    ticket_ids: list[str] = []
    feature_title: str = ""
    feature_file: str = ""
    scenario_name: str = ""
    scenario_type: str = "Scenario"
    tags: list[str] = []
    steps: list[str] = []
    source: str = "feature_file"


class RTMSearchRow(BaseModel):
    ticket_id: str = ""
    ac_id: str = ""
    scenario_name: str = ""
    feature_file: str = ""
    feature_title: str = ""
    tags: str = ""
    source: str = ""
    content: str = ""


class ExplainRequest(BaseModel):
    scenario_name: str
    include_steps: bool = True
    include_ticket_context: bool = True


class ExplainResponse(BaseModel):
    scenario_name: str
    feature_title: str
    feature_file: str
    ticket_ids: list[str]
    tags: list[str]
    steps: list[str]
    explanation: str
    rtm_rows: list[RTMSearchRow] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=list[RTMRow], summary="Full RTM listing")
def get_rtm(
    ticket: Optional[str] = Query(None, description="Filter by Jira/ADO ticket key, e.g. GDS-42"),
    feature: Optional[str] = Query(None, description="Filter by feature file name substring"),
    tag: Optional[str] = Query(None, description="Filter by @-tag substring"),
):
    """Return the full RTM built from scanning automation/features/.

    Results are filtered by ticket, feature filename, or tag when provided.
    Combines live feature-file scan with RTM KB rows (if populated by Scribe).
    """
    rows = _parse_feature_files()

    if ticket:
        ticket_upper = ticket.upper()
        rows = [r for r in rows if any(ticket_upper in t.upper() for t in r["ticket_ids"])]

    if feature:
        rows = [r for r in rows if feature.lower() in r["feature_file"].lower()]

    if tag:
        rows = [r for r in rows if any(tag.lstrip("@").lower() in t.lower() for t in r["tags"])]

    return [RTMRow(**r) for r in rows]


@router.get("/search", response_model=list[RTMSearchRow], summary="Semantic RTM search")
def search_rtm(
    q: str = Query(..., description="Natural language or keyword query, e.g. 'personal details form AC-001'"),
    limit: int = Query(10, ge=1, le=50),
):
    """Semantic search across the RTM vector KB.

    Returns persisted AC-ID → Scenario rows that were written by Scribe via
    `persist_traceability_to_rtm`. Falls back to an empty list if the KB is empty
    (i.e. Scribe hasn't run yet — use GET /rtm for the live feature-file view).
    """
    return [RTMSearchRow(**r) for r in _query_rtm_kb(q, num_results=limit)]


@router.get("/ticket/{ticket_key}", response_model=list[RTMRow], summary="Coverage for a specific ticket")
def get_rtm_by_ticket(ticket_key: str):
    """Return all scenarios that reference a specific Jira/ADO ticket key.

    Combines live feature-file scan + RTM KB rows so the answer is always
    fresh even if Scribe hasn't yet persisted traceability.
    """
    rows = _parse_feature_files()
    ticket_upper = ticket_key.upper()
    filtered = [r for r in rows if any(ticket_upper in t.upper() for t in r["ticket_ids"])]

    if not filtered:
        raise HTTPException(
            status_code=404,
            detail=f"No scenarios found referencing ticket {ticket_key}. "
                   "Run the Scribe on this ticket or add @{ticket_key} tags to your feature files.",
        )

    return [RTMRow(**r) for r in filtered]


@router.post("/explain", response_model=ExplainResponse, summary="Explain a scenario's full lineage")
def explain_scenario(body: ExplainRequest):
    """Return a human-readable explanation of a scenario — its purpose, which requirement
    it covers, what steps it executes, and the RTM context.

    Combines live feature-file parsing + RTM KB semantic search.
    """
    # Find the scenario in feature files
    all_rows = _parse_feature_files()
    match = next(
        (r for r in all_rows if body.scenario_name.lower() in r["scenario_name"].lower()),
        None,
    )

    # Also query the RTM KB for persisted traceability rows
    rtm_rows = _query_rtm_kb(body.scenario_name, num_results=5)

    if not match and not rtm_rows:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario '{body.scenario_name}' not found in feature files or RTM KB.",
        )

    if match:
        ticket_ids = match["ticket_ids"]
        tags = match["tags"]
        steps = match["steps"] if body.include_steps else []
        feature_title = match["feature_title"]
        feature_file = match["feature_file"]

        # Build explanation
        ticket_str = ", ".join(ticket_ids) if ticket_ids else "no ticket tag found"
        tag_str = " ".join(f"@{t}" for t in tags)
        step_str = "\n".join(f"  {s}" for s in steps) if steps else "  (steps not included)"

        explanation_parts = [
            f"**{match['scenario_type']}: {match['scenario_name']}**",
            f"\nThis scenario is part of the feature **\"{feature_title}\"** "
            f"defined in `{feature_file}`.",
            f"\n**Links to requirement(s):** {ticket_str}",
            f"**Tags:** {tag_str or 'none'}",
        ]

        if body.include_steps and steps:
            explanation_parts.append(f"\n**Steps:**\n{step_str}")

        if body.include_ticket_context and rtm_rows:
            ac_ids = list({r["ac_id"] for r in rtm_rows if r.get("ac_id")})
            if ac_ids:
                explanation_parts.append(f"\n**Acceptance Criteria covered:** {', '.join(ac_ids)}")

        explanation = "\n".join(explanation_parts)
    else:
        # Fallback to RTM KB data only
        r = rtm_rows[0]
        ticket_ids = [r["ticket_id"]] if r.get("ticket_id") else []
        tags = r["tags"].split() if r.get("tags") else []
        steps = []
        feature_title = r.get("feature_title", "")
        feature_file = r.get("feature_file", "")
        explanation = (
            f"**Scenario: {body.scenario_name}**\n"
            f"Found in RTM KB (traceability persisted by Scribe).\n"
            f"Ticket: {r.get('ticket_id', 'unknown')}, AC: {r.get('ac_id', 'unknown')}"
        )

    return ExplainResponse(
        scenario_name=body.scenario_name,
        feature_title=feature_title,
        feature_file=feature_file,
        ticket_ids=ticket_ids,
        tags=tags,
        steps=steps,
        explanation=explanation,
        rtm_rows=[RTMSearchRow(**r) for r in rtm_rows],
    )
