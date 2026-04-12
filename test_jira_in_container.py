"""Test Jira API from within Docker container."""
import os
import sys
import requests
from requests.auth import HTTPBasicAuth

jira_url = os.getenv("JIRA_URL")
jira_username = os.getenv("JIRA_USERNAME")
jira_api_token = os.getenv("JIRA_API_TOKEN")

print(f"JIRA_URL: {jira_url}")
print(f"JIRA_USERNAME: {jira_username}")
print(f"JIRA_API_TOKEN: ***SET***" if jira_api_token else "NOT SET")

if not jira_url or not jira_username or not jira_api_token:
    print("FAIL: Missing environment variables")
    sys.exit(1)

# Test authentication
print("\nTesting authentication...")
api_url = f"{jira_url}/rest/api/3/myself"
response = requests.get(
    api_url,
    auth=HTTPBasicAuth(jira_username, jira_api_token),
    headers={"Accept": "application/json"},
    timeout=10,
)
print(f"Auth Status: {response.status_code}")

if response.status_code != 200:
    print(f"FAIL: Authentication failed")
    print(response.text[:200])
    sys.exit(1)

# Test ticket fetch
print("\nTesting ticket fetch GDS-4...")
api_url = f"{jira_url}/rest/api/3/issue/GDS-4"
response = requests.get(
    api_url,
    auth=HTTPBasicAuth(jira_username, jira_api_token),
    headers={"Accept": "application/json"},
    timeout=10,
)
print(f"Ticket Status: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    print(f"SUCCESS: Ticket fetched")
    print(f"Key: {data.get('key')}")
    print(f"Summary: {data.get('fields', {}).get('summary')}")
else:
    print(f"FAIL: Ticket fetch failed")
    print(response.text[:200])
    sys.exit(1)
