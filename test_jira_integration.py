"""
Jira Integration Test Script
==============================

Test script to verify Jira API integration is working correctly.
This script tests the fetch_jira_ticket function directly.
"""

import os
import sys
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

from agents.architect.tools import fetch_jira_ticket


def test_jira_authentication():
    """Test Jira API authentication by fetching user info."""
    print("=" * 60)
    print("Jira Authentication Test")
    print("=" * 60)
    
    jira_url = os.getenv("JIRA_URL", "https://lokeshsharma2.atlassian.net")
    jira_username = os.getenv("JIRA_USERNAME")
    jira_api_token = os.getenv("JIRA_API_TOKEN")
    
    print(f"\nEnvironment Variables:")
    print(f"  JIRA_URL: {jira_url}")
    print(f"  JIRA_USERNAME: {jira_username}")
    print(f"  JIRA_API_TOKEN: {'***SET***' if jira_api_token else 'NOT SET'}")
    print(f"  API Token Length: {len(jira_api_token) if jira_api_token else 0}")
    
    if not jira_username or not jira_api_token:
        print("\n❌ FAIL: Missing required environment variables")
        return False
    
    try:
        # Test authentication by fetching user info
        api_url = f"{jira_url}/rest/api/3/myself"
        print(f"\nTesting API endpoint: {api_url}")
        print(f"Using HTTP Basic Auth with username: {jira_username}")
        
        response = requests.get(
            api_url,
            auth=HTTPBasicAuth(jira_username, jira_api_token),
            headers={"Accept": "application/json"},
            timeout=10,
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"\n✅ SUCCESS: Authentication working")
            print(f"  User Email: {user_data.get('emailAddress', 'N/A')}")
            print(f"  Display Name: {user_data.get('displayName', 'N/A')}")
            return True
        elif response.status_code == 401:
            print(f"\n❌ FAIL: Authentication failed (HTTP 401)")
            print(f"  This usually means:")
            print(f"  1. The API token is incorrect or expired")
            print(f"  2. The email address is not correct for this Atlassian account")
            print(f"  3. The API token was generated for a different Atlassian account")
            print(f"\n  Please verify:")
            print(f"  - Generate a new API token at: https://id.atlassian.com/manage-profile/security/api-tokens")
            print(f"  - Ensure the email matches your Atlassian account")
            print(f"  - Ensure the Jira URL is correct for your instance")
            return False
        elif response.status_code == 403:
            print(f"\n❌ FAIL: Access forbidden (HTTP 403)")
            print(f"  This usually means the user doesn't have permission to access this resource")
            return False
        else:
            print(f"\n❌ FAIL: Authentication failed with HTTP {response.status_code}")
            print(f"  Response: {response.text[:500]}")
            return False
            
    except Exception as e:
        print(f"\n❌ FAIL: Exception occurred: {e}")
        return False


def test_jira_ticket_fetch(ticket_key):
    """Test Jira API integration by fetching a specific ticket."""
    print("\n" + "=" * 60)
    print(f"Jira Ticket Fetch Test: {ticket_key}")
    print("=" * 60)
    
    print(f"\nTesting fetch_jira_ticket for ticket: {ticket_key}")
    print("-" * 60)
    
    try:
        result = fetch_jira_ticket(ticket_key)
        
        if "error" in result:
            print(f"❌ FAIL: {result['error']}")
            print(f"   Ticket Key: {result.get('ticket_key')}")
            return False
        
        print("✅ SUCCESS: Ticket fetched successfully")
        print(f"\nTicket Details:")
        print(f"  Ticket Key: {result.get('ticket_key')}")
        print(f"  Ticket URL: {result.get('ticket_url')}")
        print(f"  Summary: {result.get('summary')}")
        print(f"  Status: {result.get('status')}")
        print(f"  Priority: {result.get('priority')}")
        print(f"  Project Key: {result.get('project_key')}")
        
        # Description may be a dict (Atlassian Document Format) or string
        description = result.get('description')
        if isinstance(description, dict):
            print(f"  Description: (Atlassian Document Format - {len(str(description))} chars)")
        elif description:
            print(f"  Description: {description[:100]}...")
        else:
            print(f"  Description: (empty)")
        
        return True
        
    except Exception as e:
        import traceback
        print(f"❌ FAIL: Exception occurred: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False


def test_jira_project_list():
    """Test Jira API by listing accessible projects."""
    print("\n" + "=" * 60)
    print("Jira Project List Test")
    print("=" * 60)
    
    jira_url = os.getenv("JIRA_URL", "https://lokeshsharma2.atlassian.net")
    jira_username = os.getenv("JIRA_USERNAME")
    jira_api_token = os.getenv("JIRA_API_TOKEN")
    
    try:
        api_url = f"{jira_url}/rest/api/3/project"
        response = requests.get(
            api_url,
            auth=HTTPBasicAuth(jira_username, jira_api_token),
            headers={"Accept": "application/json"},
            timeout=10,
        )
        
        if response.status_code == 200:
            projects = response.json()
            print(f"\n✅ SUCCESS: Found {len(projects)} accessible projects")
            print("\nProjects:")
            for project in projects[:5]:  # Show first 5 projects
                print(f"  - {project.get('key')}: {project.get('name')}")
            if len(projects) > 5:
                print(f"  ... and {len(projects) - 5} more")
            return True
        else:
            print(f"\n❌ FAIL: Failed to list projects with HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"\n❌ FAIL: Exception occurred: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Jira Integration Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Authentication
    results.append(("Authentication", test_jira_authentication()))
    
    # Test 2: List projects
    results.append(("Project List", test_jira_project_list()))
    
    # Test 3: Fetch specific ticket (you can change this to an actual ticket)
    ticket_key = "GDS-4"  # Change this to an actual ticket key if needed
    results.append(("Ticket Fetch", test_jira_ticket_fetch(ticket_key)))
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {test_name}: {status}")
    
    overall_success = all(result[1] for result in results)
    print("\n" + "=" * 60)
    if overall_success:
        print("All Tests: PASSED ✅")
    else:
        print("Some Tests: FAILED ❌")
    print("=" * 60)
    
    sys.exit(0 if overall_success else 1)
