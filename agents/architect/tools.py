"""
Architect Agent Tools
======================

Custom tools for the Architect agent.
"""

import logging
import os
from typing import Optional

import requests
from agno.tools import tool
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


def _adf_to_text(node: object) -> str:
    """Convert Atlassian Document Format (ADF) node to plain text."""
    if not isinstance(node, dict):
        return ""
    node_type = node.get("type", "")
    if node_type == "text":
        return node.get("text", "")
    children = node.get("content", [])
    parts = [_adf_to_text(c) for c in children]
    sep = "\n" if node_type in ("paragraph", "bulletList", "orderedList", "listItem", "heading") else ""
    return sep.join(p for p in parts if p).strip()


@tool(
    name="fetch_jira_ticket",
    description="Fetch Jira ticket details using direct Jira REST API call"
)
def fetch_jira_ticket(ticket_key: str) -> dict:
    """Fetch Jira ticket details using direct API call.

    Args:
        ticket_key: Jira ticket key (e.g., "GDS-123")

    Returns:
        Dictionary containing ticket details or error message.
    """
    # Support both JIRA_* and ATLASSIAN_* env var naming conventions
    jira_url = (
        os.getenv("JIRA_URL")
        or os.getenv("ATLASSIAN_URL", "https://lokeshsharma2.atlassian.net")
    )
    jira_username = os.getenv("JIRA_USERNAME") or os.getenv("ATLASSIAN_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")

    if not jira_username or not jira_api_token:
        logger.warning("Jira credentials not configured - cannot fetch ticket")
        return {
            "error": "Jira credentials not configured",
            "ticket_key": ticket_key,
        }

    try:
        # Construct API URL
        api_url = f"{jira_url}/rest/api/3/issue/{ticket_key}"

        # Make API request
        response = requests.get(
            api_url,
            auth=HTTPBasicAuth(jira_username, jira_api_token),
            headers={"Accept": "application/json"},
            timeout=10,
        )

        if response.status_code == 200:
            ticket_data = response.json()
            fields = ticket_data.get("fields", {})
            # Description may be Atlassian Document Format (ADF) object or plain string
            raw_desc = fields.get("description", "")
            if isinstance(raw_desc, dict):
                description = _adf_to_text(raw_desc)
            else:
                description = raw_desc or ""
            # Extract acceptance criteria from custom field (common names)
            ac_text = ""
            for cf_key in ("customfield_10016", "customfield_10014", "customfield_10028"):
                cf_val = fields.get(cf_key)
                if cf_val:
                    if isinstance(cf_val, dict):
                        ac_text = _adf_to_text(cf_val)
                    elif isinstance(cf_val, str):
                        ac_text = cf_val
                    if ac_text:
                        break
            # Extract issue links (linked requirements, blocks, relates to, etc.)
            raw_links = fields.get("issuelinks", [])
            issue_links = []
            for link in raw_links:
                link_type = link.get("type", {})
                direction = "inward" if "inwardIssue" in link else "outward"
                linked_issue = link.get("inwardIssue") or link.get("outwardIssue") or {}
                link_label = link_type.get("inward" if direction == "inward" else "outward", "")
                issue_links.append({
                    "link_type": link_type.get("name", ""),
                    "direction": direction,
                    "label": link_label,
                    "linked_key": linked_issue.get("key", ""),
                    "linked_summary": linked_issue.get("fields", {}).get("summary", ""),
                    "linked_status": linked_issue.get("fields", {}).get("status", {}).get("name", ""),
                    "linked_url": f"{jira_url}/browse/{linked_issue.get('key', '')}",
                })
            # Extract reporter and assignee
            reporter = fields.get("reporter") or {}
            assignee = fields.get("assignee") or {}
            return {
                "ticket_key": ticket_key,
                "ticket_url": f"{jira_url}/browse/{ticket_key}",
                "summary": fields.get("summary", ""),
                "description": description,
                "acceptance_criteria": ac_text,
                "status": fields.get("status", {}).get("name", "") if fields.get("status") else "",
                "priority": fields.get("priority", {}).get("name", "") if fields.get("priority") else "",
                "project_key": fields.get("project", {}).get("key", "") if fields.get("project") else "",
                "labels": fields.get("labels", []),
                "components": [c.get("name", "") for c in fields.get("components", [])],
                "issue_links": issue_links,
                "reporter": reporter.get("displayName", ""),
                "assignee": assignee.get("displayName", ""),
                "issue_type": fields.get("issuetype", {}).get("name", ""),
            }
        else:
            logger.error(f"Failed to fetch ticket {ticket_key}: {response.status_code}")
            return {
                "error": f"Failed to fetch ticket: HTTP {response.status_code}",
                "ticket_key": ticket_key,
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Jira ticket {ticket_key}: {e}")
        return {
            "error": f"Request failed: {str(e)}",
            "ticket_key": ticket_key,
        }


@tool(
    name="add_jira_comment",
    description="Add a comment to a Jira ticket",
    requires_confirmation=True,
)
def add_jira_comment(ticket_id: str, comment: str, requirement_context_id: str = "") -> dict:
    """Add a comment to a Jira ticket.

    Args:
        ticket_id: Jira ticket ID (e.g., "QA-123")
        comment: The comment text to add (free-form text)
        requirement_context_id: Link to RequirementContext (optional)

    Returns:
        Dictionary containing result or error message.
    """
    jira_url = os.getenv("JIRA_URL", "https://lokeshsharma2.atlassian.net")
    jira_username = os.getenv("JIRA_USERNAME")
    jira_api_token = os.getenv("JIRA_API_TOKEN")

    if not jira_username or not jira_api_token:
        logger.warning("Jira credentials not configured - cannot add comment")
        return {
            "error": "Jira credentials not configured",
            "ticket_id": ticket_id,
        }

    try:
        # Construct API URL
        api_url = f"{jira_url}/rest/api/3/issue/{ticket_id}/comment"

        # Add RequirementContext link to comment if provided
        if requirement_context_id:
            comment += f"\n\nRequirementContext Link: {requirement_context_id}"

        # Make API request
        # Jira Cloud REST API v3 requires body in Atlassian Document Format (ADF).
        # Plain strings return HTTP 400. Convert each paragraph (blank-line separated)
        # into an ADF paragraph node so markdown tables and bullet lists are preserved
        # as readable text in the Jira comment.
        paragraphs = []
        for para in comment.split("\n\n"):
            stripped = para.strip()
            if stripped:
                paragraphs.append({
                    "type": "paragraph",
                    "content": [{"type": "text", "text": stripped}]
                })

        adf_body = {
            "version": 1,
            "type": "doc",
            "content": paragraphs or [{"type": "paragraph", "content": [{"type": "text", "text": comment}]}]
        }

        response = requests.post(
            api_url,
            auth=HTTPBasicAuth(jira_username, jira_api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json={"body": adf_body},
            timeout=10,
        )

        if response.status_code == 201:
            comment_data = response.json()
            return {
                "success": True,
                "ticket_id": ticket_id,
                "comment_id": comment_data.get("id"),
                "message": f"Comment added to ticket {ticket_id}",
            }
        else:
            logger.error(f"Failed to add comment to {ticket_id}: {response.status_code}")
            return {
                "error": f"Failed to add comment: HTTP {response.status_code}",
                "ticket_id": ticket_id,
            }

    except requests.exceptions.RequestException as e:
        logger.error(f"Error adding comment to {ticket_id}: {e}")
        return {
            "error": f"Request failed: {str(e)}",
            "ticket_id": ticket_id,
        }


@tool(
    name="create_jira_issue",
    description="Create a new Jira issue (story, bug, task, or sub-task) in a given project",
    requires_confirmation=True,
)
def create_jira_issue(
    project_key: str,
    summary: str,
    description: str = "",
    issue_type: str = "Story",
    priority: str = "Medium",
    labels: Optional[list] = None,
    parent_key: Optional[str] = None,
) -> dict:
    """Create a new Jira issue.

    Args:
        project_key: Jira project key (e.g., "GDS")
        summary: Issue title / one-line summary
        description: Detailed description (plain text)
        issue_type: Issue type — Story, Bug, Task, Sub-task (default: Story)
        priority: Priority — Highest, High, Medium, Low, Lowest (default: Medium)
        labels: Optional list of label strings to attach
        parent_key: Optional parent issue key for sub-tasks (e.g., "GDS-42")

    Returns:
        Dictionary with created issue key, URL, and id on success, or error details.
    """
    jira_url = (
        os.getenv("JIRA_URL")
        or os.getenv("ATLASSIAN_URL", "https://lokeshsharma2.atlassian.net")
    )
    jira_username = os.getenv("JIRA_USERNAME") or os.getenv("ATLASSIAN_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")

    if not jira_username or not jira_api_token:
        logger.warning("Jira credentials not configured - cannot create issue")
        return {"error": "Jira credentials not configured"}

    fields: dict = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
        "priority": {"name": priority},
        "description": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": description or summary}],
                }
            ],
        },
    }
    if labels:
        fields["labels"] = labels
    if parent_key:
        fields["parent"] = {"key": parent_key}

    try:
        response = requests.post(
            f"{jira_url}/rest/api/3/issue",
            auth=HTTPBasicAuth(jira_username, jira_api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json={"fields": fields},
            timeout=10,
        )
        if response.status_code == 201:
            data = response.json()
            key = data.get("key", "")
            return {
                "success": True,
                "issue_key": key,
                "issue_id": data.get("id", ""),
                "issue_url": f"{jira_url}/browse/{key}",
                "message": f"Issue {key} created in project {project_key}",
            }
        logger.error(f"Failed to create Jira issue: {response.status_code} {response.text}")
        return {"error": f"Failed to create issue: HTTP {response.status_code}", "detail": response.text}
    except requests.exceptions.RequestException as e:
        logger.error(f"Error creating Jira issue: {e}")
        return {"error": f"Request failed: {str(e)}"}


@tool(
    name="fetch_linked_issues",
    description=(
        "Fetch the full details of all issues linked to a given Jira ticket "
        "(e.g. 'relates to', 'is blocked by', 'is required by', 'linked requirement'). "
        "Call this after fetch_jira_ticket to enrich the analysis with linked requirements."
    ),
)
def fetch_linked_issues(ticket_key: str) -> dict:
    """Fetch full details of every issue linked to *ticket_key*.

    Returns a dict with:
    - ``parent_key``: the ticket we fetched links from
    - ``linked_issues``: list of dicts, each containing the full fields of one linked issue
      (key, summary, description, acceptance_criteria, status, priority, issue_type, issue_links)

    Args:
        ticket_key: Parent Jira ticket key (e.g. "GDS-8")
    """
    jira_url = (
        os.getenv("JIRA_URL")
        or os.getenv("ATLASSIAN_URL", "https://lokeshsharma2.atlassian.net")
    )
    jira_username = os.getenv("JIRA_USERNAME") or os.getenv("ATLASSIAN_EMAIL")
    jira_api_token = os.getenv("JIRA_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN")

    if not jira_username or not jira_api_token:
        return {"error": "Jira credentials not configured", "ticket_key": ticket_key}

    auth = HTTPBasicAuth(jira_username, jira_api_token)
    headers = {"Accept": "application/json"}

    # -----------------------------------------------------------------------
    # 1. Fetch the parent ticket to extract its issuelinks list
    # -----------------------------------------------------------------------
    try:
        parent_resp = requests.get(
            f"{jira_url}/rest/api/3/issue/{ticket_key}?fields=issuelinks,summary",
            auth=auth,
            headers=headers,
            timeout=10,
        )
        if parent_resp.status_code != 200:
            return {
                "error": f"Failed to fetch parent ticket: HTTP {parent_resp.status_code}",
                "ticket_key": ticket_key,
            }
        parent_data = parent_resp.json()
        raw_links = parent_data.get("fields", {}).get("issuelinks", [])
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}", "ticket_key": ticket_key}

    if not raw_links:
        return {
            "parent_key": ticket_key,
            "linked_issues": [],
            "message": "No linked issues found on this ticket.",
        }

    # -----------------------------------------------------------------------
    # 2. Collect linked issue keys (deduplicated)
    # -----------------------------------------------------------------------
    linked_keys: list[str] = []
    link_metadata: dict[str, dict] = {}
    for link in raw_links:
        link_type = link.get("type", {})
        direction = "inward" if "inwardIssue" in link else "outward"
        linked_issue = link.get("inwardIssue") or link.get("outwardIssue") or {}
        key = linked_issue.get("key", "")
        if key and key not in linked_keys:
            linked_keys.append(key)
            link_metadata[key] = {
                "link_type": link_type.get("name", ""),
                "direction": direction,
                "label": link_type.get("inward" if direction == "inward" else "outward", ""),
            }

    # -----------------------------------------------------------------------
    # 3. Fetch each linked issue in detail
    # -----------------------------------------------------------------------
    linked_issues: list[dict] = []
    for key in linked_keys:
        try:
            resp = requests.get(
                f"{jira_url}/rest/api/3/issue/{key}",
                auth=auth,
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                linked_issues.append({
                    "key": key,
                    "error": f"HTTP {resp.status_code}",
                    **link_metadata.get(key, {}),
                })
                continue
            data = resp.json()
            fields = data.get("fields", {})
            raw_desc = fields.get("description", "")
            description = _adf_to_text(raw_desc) if isinstance(raw_desc, dict) else (raw_desc or "")
            ac_text = ""
            for cf_key in ("customfield_10016", "customfield_10014", "customfield_10028"):
                cf_val = fields.get(cf_key)
                if cf_val:
                    ac_text = _adf_to_text(cf_val) if isinstance(cf_val, dict) else str(cf_val)
                    if ac_text:
                        break
            linked_issues.append({
                "key": key,
                "url": f"{jira_url}/browse/{key}",
                "summary": fields.get("summary", ""),
                "description": description,
                "acceptance_criteria": ac_text,
                "status": (fields.get("status") or {}).get("name", ""),
                "priority": (fields.get("priority") or {}).get("name", ""),
                "issue_type": (fields.get("issuetype") or {}).get("name", ""),
                **link_metadata.get(key, {}),
            })
        except requests.exceptions.RequestException as e:
            linked_issues.append({"key": key, "error": str(e), **link_metadata.get(key, {})})

    return {
        "parent_key": ticket_key,
        "linked_count": len(linked_issues),
        "linked_issues": linked_issues,
    }


# ---------------------------------------------------------------------------
# Document Library KB Population
# ---------------------------------------------------------------------------

@tool(
    name="index_ticket_to_document_library",
    description=(
        "Persist a Jira/ADO ticket's full content into the Document Library vector KB so every "
        "agent can query it semantically. Call this immediately after fetch_jira_ticket succeeds."
    ),
)
def index_ticket_to_document_library(
    ticket_key: str,
    summary: str,
    description: str,
    acceptance_criteria: str = "",
    status: str = "",
    priority: str = "",
    issue_type: str = "",
    ticket_url: str = "",
    project_key: str = "",
    labels: str = "",
) -> str:
    """Write a Jira/ADO ticket into the Document Library vector KB.

    Stored as a plain-text document that hybrid search can retrieve::

        Ticket: GDS-42
        Summary: Personal Details Form — capture and validate user information
        Status: In Progress
        Priority: High
        Type: Story
        Project: GDS
        Labels: gds, form, personal-details
        URL: https://...atlassian.net/browse/GDS-42

        Description:
        ...

        Acceptance Criteria:
        ...

    Args:
        ticket_key:           Jira/ADO issue key
        summary:              One-line title
        description:          Full description text (plain text, not ADF)
        acceptance_criteria:  Extracted AC text
        status:               Current issue status
        priority:             Issue priority
        issue_type:           Story / Bug / Task etc.
        ticket_url:           Direct link to the issue
        project_key:          Jira project key
        labels:               Comma/space-separated labels

    Returns:
        Status string confirming indexing.
    """
    from db.session import get_document_library_kb

    doc_text = (
        f"Ticket: {ticket_key}\n"
        f"Summary: {summary}\n"
        f"Status: {status}\n"
        f"Priority: {priority}\n"
        f"Type: {issue_type}\n"
        f"Project: {project_key}\n"
        f"Labels: {labels}\n"
        f"URL: {ticket_url}\n"
        f"\nDescription:\n{description}\n"
        f"\nAcceptance Criteria:\n{acceptance_criteria}\n"
    )

    try:
        doc_lib = get_document_library_kb()
        doc_lib.load_text(
            text=doc_text,
            metadata={
                "ticket_id": ticket_key,
                "summary": summary,
                "status": status,
                "priority": priority,
                "issue_type": issue_type,
                "project_key": project_key,
                "ticket_url": ticket_url,
                "labels": labels,
                "source": "jira",
            },
        )
        return f"Indexed ticket {ticket_key} into Document Library KB."
    except Exception as e:
        logger.error(f"Failed to index ticket {ticket_key} to document library: {e}")
        return f"ERROR: Failed to index {ticket_key}: {e}"

