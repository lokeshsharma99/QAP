"""
Notification Integrations
===========================

Posts structured RCA reports to Microsoft Teams (via Power Automate) and
to Slack (via slack_sdk) when the Detective completes failure classification.

HITL Gate pattern  (same for both tools)
-----------------------------------------
Both post_rca_to_teams and post_rca_to_slack carry requires_confirmation=True.
When the Detective calls either:

  1. Agno writes one approval record to the DB and pauses the run.
  2. The approval surfaces simultaneously in:
       /approvals  — Human Lead clicks Approve / Reject
       Chat run    — stream pauses showing "pending approval"
  3. On approval the tool executes and sends the notification.
  4. The pipeline then continues to the Healable Check gate.

Environment variables
---------------------
  POWER_AUTOMATE_TEAMS_URL   — full HTTP-trigger URL from the Power Automate flow.
  SLACK_BOT_TOKEN            — xoxb-... token for your Slack bot.
  SLACK_CHANNEL              — channel ID (e.g. C0B12TFRR7V) or name (#channel).
"""

import logging
import os
from typing import Optional

import requests
from agno.tools import tool

try:
    from slack_sdk import WebClient as _SlackWebClient
    from slack_sdk.errors import SlackApiError as _SlackApiError
except ImportError:  # pragma: no cover
    _SlackWebClient = None  # type: ignore[assignment,misc]
    _SlackApiError = Exception  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_FLOW_URL = os.getenv("POWER_AUTOMATE_TEAMS_URL", "")
_SLACK_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
_SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_rca_card(
    test_name: str,
    classification: str,
    confidence: float,
    root_cause: str,
    affected_file: str,
    suggested_fix: str,
    requires_human: bool,
) -> dict:
    """Build the Teams Adaptive Card payload for an RCA report."""
    confidence_pct = f"{int(confidence * 100)}%"
    severity_color = (
        "attention" if requires_human or confidence < 0.80
        else "warning" if confidence < 0.99
        else "good"
    )
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": "🔍 Quality Autopilot — RCA Report",
                            "weight": "Bolder",
                            "size": "Medium",
                        },
                        {
                            "type": "FactSet",
                            "facts": [
                                {"title": "Test",           "value": test_name},
                                {"title": "Classification", "value": classification},
                                {"title": "Confidence",     "value": confidence_pct},
                                {"title": "Affected File",  "value": affected_file},
                            ],
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Root Cause:** {root_cause}",
                            "wrap": True,
                        },
                        {
                            "type": "TextBlock",
                            "text": f"**Suggested Fix:** {suggested_fix}",
                            "wrap": True,
                            "color": severity_color,
                        },
                        {
                            "type": "TextBlock",
                            "text": "⚠️ Requires human intervention — LOGIC_CHANGE detected." if requires_human
                                    else "🤖 Auto-heal eligible — awaiting /approvals gate.",
                            "wrap": True,
                            "isVisible": True,
                            "color": "attention" if requires_human else "good",
                        },
                    ],
                },
            }
        ],
    }


# ---------------------------------------------------------------------------
# Tool
# ---------------------------------------------------------------------------

@tool(
    name="post_rca_to_teams",
    description=(
        "Post a structured RCA report to Microsoft Teams via the configured Power Automate flow. "
        "Requires Human Lead confirmation before executing — the approval gate surfaces in "
        "/approvals AND pauses the chat run simultaneously from the same DB record."
    ),
    requires_confirmation=True,
)
def post_rca_to_teams(
    test_name: str,
    classification: str,
    confidence: float,
    root_cause: str,
    affected_file: str,
    suggested_fix: str,
    requires_human: bool = False,
    extra_message: Optional[str] = None,
) -> dict:
    """Post an RCA report to Microsoft Teams via Power Automate.

    Args:
        test_name: Name of the failing test or test suite.
        classification: RCA classification — LOCATOR_STALE, DATA_MISMATCH,
                        TIMING_FLAKE, ENV_FAILURE, or LOGIC_CHANGE.
        confidence: Confidence score 0.0–1.0.
        root_cause: Human-readable root cause explanation.
        affected_file: Path to the failing test/POM file.
        suggested_fix: What the Medic should do, or manual action required.
        requires_human: True if LOGIC_CHANGE or confidence < 0.80.
        extra_message: Optional freeform text appended below the card.

    Returns:
        dict with success/error status and HTTP response code.
    """
    flow_url = _FLOW_URL or os.getenv("POWER_AUTOMATE_TEAMS_URL", "")
    if not flow_url:
        logger.warning("POWER_AUTOMATE_TEAMS_URL not set — skipping Teams notification")
        return {
            "success": False,
            "skipped": True,
            "reason": "POWER_AUTOMATE_TEAMS_URL not configured",
        }

    card = _build_rca_card(
        test_name=test_name,
        classification=classification,
        confidence=confidence,
        root_cause=root_cause,
        affected_file=affected_file,
        suggested_fix=suggested_fix,
        requires_human=requires_human,
    )

    # Power Automate HTTP trigger accepts the Teams card as the payload.
    # The flow is responsible for forwarding it to the Teams channel via
    # a "Post adaptive card in a chat or channel" action.
    payload: dict = {**card}
    if extra_message:
        payload["extra_message"] = extra_message

    try:
        response = requests.post(flow_url, json=payload, timeout=15)
        if response.status_code in (200, 202):
            logger.info(f"RCA report for '{test_name}' posted to Teams (HTTP {response.status_code})")
            return {
                "success": True,
                "test_name": test_name,
                "classification": classification,
                "http_status": response.status_code,
                "message": f"RCA report for '{test_name}' posted to Teams channel.",
            }
        logger.error(f"Teams POST failed: HTTP {response.status_code} — {response.text[:200]}")
        return {
            "success": False,
            "http_status": response.status_code,
            "error": f"Flow returned HTTP {response.status_code}",
            "detail": response.text[:200],
        }
    except requests.exceptions.RequestException as exc:
        logger.error(f"Teams notification failed: {exc}")
        return {
            "success": False,
            "error": f"Request failed: {str(exc)}",
        }


# ---------------------------------------------------------------------------
# Slack notification tool
# ---------------------------------------------------------------------------

@tool(
    name="post_rca_to_slack",
    description=(
        "Post a structured RCA report to Slack via the configured bot. "
        "Requires Human Lead confirmation before executing — the approval gate surfaces in "
        "/approvals AND pauses the chat run simultaneously from the same DB record."
    ),
    requires_confirmation=True,
)
def post_rca_to_slack(
    test_name: str,
    classification: str,
    confidence: float,
    root_cause: str,
    affected_file: str,
    suggested_fix: str,
    requires_human: bool = False,
    extra_message: Optional[str] = None,
) -> dict:
    """Post an RCA report to Slack using the configured bot token.

    Args:
        test_name: Name of the failing test or test suite.
        classification: RCA classification — LOCATOR_STALE, DATA_MISMATCH,
                        TIMING_FLAKE, ENV_FAILURE, or LOGIC_CHANGE.
        confidence: Confidence score 0.0–1.0.
        root_cause: Human-readable root cause explanation.
        affected_file: Path to the failing test/POM file.
        suggested_fix: What the Medic should do, or manual action required.
        requires_human: True if LOGIC_CHANGE or confidence < 0.80.
        extra_message: Optional freeform text appended at the end.

    Returns:
        dict with success/error status and Slack message timestamp.
    """
    if _SlackWebClient is None:
        return {"success": False, "error": "slack_sdk not installed"}

    token = _SLACK_TOKEN or os.getenv("SLACK_BOT_TOKEN", "")
    channel = _SLACK_CHANNEL or os.getenv("SLACK_CHANNEL", "")

    if not token:
        logger.warning("SLACK_BOT_TOKEN not set — skipping Slack notification")
        return {"success": False, "skipped": True, "reason": "SLACK_BOT_TOKEN not configured"}
    if not channel:
        logger.warning("SLACK_CHANNEL not set — skipping Slack notification")
        return {"success": False, "skipped": True, "reason": "SLACK_CHANNEL not configured"}

    confidence_pct = f"{int(confidence * 100)}%"
    status_emoji = "🚨" if requires_human else ("⚠️" if confidence < 0.99 else "✅")
    action_line = (
        "⚠️ *Requires human intervention* — LOGIC_CHANGE detected." if requires_human
        else "🤖 Auto-heal eligible — proceeding to Medic."
    )

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"{status_emoji} Quality Autopilot — RCA Report"},
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Test:*\n{test_name}"},
                {"type": "mrkdwn", "text": f"*Classification:*\n{classification}"},
                {"type": "mrkdwn", "text": f"*Confidence:*\n{confidence_pct}"},
                {"type": "mrkdwn", "text": f"*Affected File:*\n`{affected_file}`"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Root Cause:*\n{root_cause}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*Suggested Fix:*\n{suggested_fix}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": action_line},
        },
    ]

    if extra_message:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": extra_message},
        })

    try:
        client = _SlackWebClient(token=token)
        resp = client.chat_postMessage(
            channel=channel,
            text=f"{status_emoji} RCA Report — {test_name} ({classification})",
            blocks=blocks,
        )
        ts = resp.get("ts", "")
        logger.info(f"RCA report for '{test_name}' posted to Slack (ts={ts})")
        return {
            "success": True,
            "test_name": test_name,
            "classification": classification,
            "slack_ts": ts,
            "message": f"RCA report for '{test_name}' posted to Slack channel.",
        }
    except _SlackApiError as exc:
        logger.error(f"Slack API error: {exc.response['error']}")
        return {"success": False, "error": exc.response["error"]}
    except Exception as exc:
        logger.error(f"Slack notification failed: {exc}")
        return {"success": False, "error": str(exc)}
