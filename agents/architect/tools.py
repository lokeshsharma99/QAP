"""
Architect Agent Tools
======================

Custom tools for the Architect agent.
"""

import logging
import os
from typing import Optional

import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


def fetch_jira_ticket(ticket_key: str) -> dict:
    """Fetch Jira ticket details using direct API call.

    Args:
        ticket_key: Jira ticket key (e.g., "GDS-123")

    Returns:
        Dictionary containing ticket details or error message.
    """
    jira_url = os.getenv("JIRA_URL", "https://lokeshsharma2.atlassian.net")
    jira_username = os.getenv("JIRA_USERNAME")
    jira_api_token = os.getenv("JIRA_API_TOKEN")

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
            return {
                "ticket_key": ticket_key,
                "ticket_url": f"{jira_url}/browse/{ticket_key}",
                "summary": ticket_data.get("fields", {}).get("summary", ""),
                "description": ticket_data.get("fields", {}).get("description", ""),
                "status": ticket_data.get("fields", {}).get("status", {}).get("name", ""),
                "priority": ticket_data.get("fields", {}).get("priority", {}).get("name", ""),
                "project_key": ticket_data.get("fields", {}).get("project", {}).get("key", ""),
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
        response = requests.post(
            api_url,
            auth=HTTPBasicAuth(jira_username, jira_api_token),
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            json={"body": comment},
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
