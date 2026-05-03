"""Quick Jira integration health check. Run: python -m scripts._test_jira"""
import os
import sys
import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

jira_url = os.getenv("JIRA_URL", "").rstrip("/")
username = os.getenv("JIRA_USERNAME") or os.getenv("ATLASSIAN_EMAIL", "")
token = os.getenv("JIRA_API_TOKEN") or os.getenv("ATLASSIAN_API_TOKEN", "")
atlassian_mcp_url = os.getenv("ATLASSIAN_MCP_URL", "http://localhost:8933/mcp")

print(f"Jira URL   : {jira_url}")
print(f"Username   : {username}")
print(f"Token set  : {'YES' if token else 'NO'}")
print(f"MCP URL    : {atlassian_mcp_url}")
print()

auth = HTTPBasicAuth(username, token)
headers = {"Accept": "application/json"}

# --- Test 1: Auth ---
r = requests.get(f"{jira_url}/rest/api/3/myself", auth=auth, headers=headers, timeout=10)
print(f"[1] Auth check          : HTTP {r.status_code}", end="")
if r.status_code == 200:
    d = r.json()
    print(f" — {d.get('displayName')} ({d.get('emailAddress')})")
else:
    print(f"\n    ERROR: {r.text[:200]}")

# --- Test 2: Project GDS ---
r = requests.get(f"{jira_url}/rest/api/3/project/GDS", auth=auth, headers=headers, timeout=10)
print(f"[2] Project GDS         : HTTP {r.status_code}", end="")
if r.status_code == 200:
    print(f" — {r.json().get('name')}")
else:
    print(f"\n    ERROR: {r.text[:200]}")

# --- Test 3: Ticket GDS-177 ---
r = requests.get(f"{jira_url}/rest/api/3/issue/GDS-177", auth=auth, headers=headers, timeout=10)
print(f"[3] Ticket GDS-177      : HTTP {r.status_code}", end="")
if r.status_code == 200:
    fields = r.json().get("fields", {})
    print(f" — {fields.get('summary')} [{fields.get('status', {}).get('name')}]")
else:
    print(f"\n    ERROR: {r.text[:300]}")

# --- Test 4: atlassian-mcp HTTP reachable ---
import socket, urllib.parse
parsed = urllib.parse.urlparse(atlassian_mcp_url)
host = parsed.hostname or "localhost"
port = parsed.port or 8933
try:
    with socket.create_connection((host, port), timeout=3):
        print(f"[4] atlassian-mcp HTTP  : REACHABLE at {host}:{port}")
except OSError as e:
    print(f"[4] atlassian-mcp HTTP  : UNREACHABLE ({e})")
