"""
Azure DevOps Tools
==================

Tools for interacting with Azure DevOps API to read CI pipeline logs and create work items.
"""

import base64
import os
from typing import Optional

import httpx
from agno.approval import approval
from agno.tools import tool
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Azure DevOps configuration
AZURE_DEVOPS_URL = os.getenv("AZURE_DEVOPS_URL")
AZURE_DEVOPS_EMAIL = os.getenv("AZURE_DEVOPS_EMAIL")
AZURE_DEVOPS_PAT = os.getenv("AZURE_DEVOPS_PAT")


def get_auth_headers() -> dict:
    """Get authentication headers for Azure DevOps API."""
    # Azure DevOps requires base64-encoded credentials for Basic auth
    auth_string = f"{AZURE_DEVOPS_EMAIL}:{AZURE_DEVOPS_PAT}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()
    return {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/json",
    }


@tool
def get_pipeline_runs(project: str, pipeline_id: str, top: int = 10) -> str:
    """Fetch recent pipeline runs for a specific pipeline.

    Args:
        project (str): Azure DevOps project name
        pipeline_id (str): Pipeline ID or name
        top (int): Number of recent runs to fetch (default: 10)

    Returns:
        str: JSON string of pipeline runs with status, timestamps, and run IDs
    """
    if not AZURE_DEVOPS_URL or not AZURE_DEVOPS_PAT:
        return "Error: Azure DevOps credentials not configured. Set AZURE_DEVOPS_URL and AZURE_DEVOPS_PAT in .env"

    try:
        url = f"{AZURE_DEVOPS_URL}/{project}/_apis/pipelines/{pipeline_id}/runs?api-version=7.0&$top={top}"
        response = httpx.get(url, headers=get_auth_headers())
        response.raise_for_status()
        
        # Parse and simplify the response to reduce context window usage
        import json
        data = response.json()
        
        # Extract only essential fields
        simplified_runs = []
        for run in data.get("value", []):
            simplified_run = {
                "id": run.get("id"),
                "name": run.get("name"),
                "state": run.get("state"),
                "result": run.get("result"),
                "createdDate": run.get("createdDate"),
                "finishedDate": run.get("finishedDate"),
                "pipeline_name": run.get("pipeline", {}).get("name"),
            }
            simplified_runs.append(simplified_run)
        
        return json.dumps({"count": len(simplified_runs), "value": simplified_runs}, indent=2)
    except Exception as e:
        return f"Error fetching pipeline runs: {str(e)}"


@approval
@tool(requires_confirmation=True)
def create_work_item(
    project: str,
    title: str,
    description: str,
    work_item_type: str = "Bug",
    assigned_to: Optional[str] = None,
) -> str:
    """Create an Azure DevOps work item/ticket with RCA findings.

    Args:
        project (str): Azure DevOps project name
        title (str): Work item title
        description (str): Work item description with RCA findings
        work_item_type (str): Type of work item (default: "Bug")
        assigned_to (str): Optional user email to assign the work item to

    Returns:
        str: Created work item ID and URL

    Note:
        This tool requires HITL approval before execution.
    """
    if not AZURE_DEVOPS_URL or not AZURE_DEVOPS_PAT:
        return "Error: Azure DevOps credentials not configured. Set AZURE_DEVOPS_URL and AZURE_DEVOPS_PAT in .env"

    try:
        # Get the work item type ID
        url = f"{AZURE_DEVOPS_URL}/{project}/_apis/wit/workitemtypes/{work_item_type}?api-version=7.0"
        response = httpx.get(url, headers=get_auth_headers())
        response.raise_for_status()
        type_info = response.json()

        # Create the work item
        url = f"{AZURE_DEVOPS_URL}/{project}/_apis/wit/workitems/${work_item_type}?api-version=7.0"
        headers = get_auth_headers()
        headers["Content-Type"] = "application/json-patch+json"

        body = [
            {"op": "add", "path": "/fields/System.Title", "value": title},
            {"op": "add", "path": "/fields/System.Description", "value": description},
        ]

        if assigned_to:
            body.append(
                {"op": "add", "path": "/fields/System.AssignedTo", "value": assigned_to}
            )

        response = httpx.patch(url, headers=headers, json=body)
        response.raise_for_status()
        result = response.json()

        work_item_id = result["id"]
        work_item_url = f"{AZURE_DEVOPS_URL}/{project}/_workitems/edit/{work_item_id}"

        return f"Work item created successfully. ID: {work_item_id}, URL: {work_item_url}"
    except Exception as e:
        return f"Error creating work item: {str(e)}"
