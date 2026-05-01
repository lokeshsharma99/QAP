"""
Shared Settings
===============

Centralizes the model, database, and environment flags
so all agents share the same resources.
"""

from os import getenv

from agno.models.openrouter import OpenRouter

from db import get_postgres_db

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
agent_db = get_postgres_db()

# ---------------------------------------------------------------------------
# Models
# Use kilo-auto/balanced when a real KILO_API_KEY is set; free otherwise.
# Mirrors the logic in demos/kilo.py.
# ---------------------------------------------------------------------------
_KILO_KEY = getenv("KILO_API_KEY", "anonymous")
_KILO_MODEL_ID = "kilo-auto/free" if _KILO_KEY == "anonymous" else "kilo-auto/balanced"

MODEL = OpenRouter(
    id=_KILO_MODEL_ID,
    base_url="https://api.kilo.ai/api/openrouter/v1",
    api_key=_KILO_KEY,
    max_tokens=None,
)

# Dedicated model for followup suggestion generation.
# Structured output is disabled so Agno uses a plain text/JSON prompt instead of
# sending response_format=Followups (which kilo-auto rejects with "Provider returned error").
FOLLOWUP_MODEL = OpenRouter(
    id=_KILO_MODEL_ID,
    base_url="https://api.kilo.ai/api/openrouter/v1",
    api_key=_KILO_KEY,
    max_tokens=2048,
    supports_native_structured_outputs=False,
)

# ---------------------------------------------------------------------------
# Followup generation patch
# Agno's default _build_followup_messages prompt doesn't request JSON output,
# so the model returns a plain text list that fails JSON parsing.
# Patch the module-level function to append explicit JSON format instructions,
# and patch the parser to handle both JSON and numbered/bulleted plain text.
# ---------------------------------------------------------------------------
import re as _re
import json as _json
from agno.run.agent import Followups as _Followups
from agno.models.message import Message as _Message
import agno.agent._response as _agno_resp

_orig_build = _agno_resp._build_followup_messages


def _patched_build_followup_messages(response_content, num_suggestions, user_message=None):
    messages = _orig_build(response_content, num_suggestions, user_message)
    last = messages[-1]
    json_instruction = (
        '\n\nRespond ONLY with a valid JSON object — no markdown, no extra text:\n'
        '{"suggestions": ["suggestion 1", "suggestion 2", "suggestion 3"]}'
    )
    messages[-1] = _Message(role=last.role, content=(last.content or '') + json_instruction)
    return messages


_orig_parse = _agno_resp._parse_followups_response


def _patched_parse_followups_response(model_response):
    # Strip <reasoning>...</reasoning> blocks that some models prepend before JSON
    content = model_response.content or ''
    content_stripped = _re.sub(r'<reasoning>.*?</reasoning>', '', content, flags=_re.DOTALL).strip()
    if content_stripped != content:
        # Temporarily swap content for the original parser
        orig_content = model_response.content
        model_response.content = content_stripped
        result = _orig_parse(model_response)
        model_response.content = orig_content
        if result:
            return result
        content = content_stripped
    else:
        # Try the original parser first (handles structured + JSON content)
        result = _orig_parse(model_response)
        if result:
            return result

    # Fallback: extract from plain text numbered/bulleted list
    # Strip any markdown code fences and try JSON again
    stripped = _re.sub(r'```[a-z]*\n?', '', content).strip().rstrip('`').strip()
    try:
        data = _json.loads(stripped)
        obj = _Followups.model_validate(data)
        if obj.suggestions:
            return obj.suggestions
    except Exception:
        pass

    # Last resort: extract numbered or bulleted lines
    lines = [
        _re.sub(r'^[\s\d\.\-\*\u2022]+', '', line).strip()
        for line in content.split('\n')
        if _re.match(r'^\s*[\d\.\-\*\u2022]', line)
    ]
    lines = [l for l in lines if 5 < len(l) < 120]
    if lines:
        return lines[:3]

    return None


_agno_resp._build_followup_messages = _patched_build_followup_messages
_agno_resp._parse_followups_response = _patched_parse_followups_response


def _patched_get_followups_response_format(model):
    # Return None so Agno does NOT set response_format on the model call.
    # The patched _build_followup_messages already appends explicit JSON
    # instructions to the prompt, so the model returns parseable JSON as
    # plain text. Passing response_format={"type":"json_object"} causes
    # providers like SiliconFlow to reject the request (code 20024).
    return None


_agno_resp._get_followups_response_format = _patched_get_followups_response_format

# ---------------------------------------------------------------------------
# Additional LLM provider credentials (used by /model/switch endpoint)
# ---------------------------------------------------------------------------
GITHUB_COPILOT_BASE_URL = getenv("GITHUB_COPILOT_BASE_URL", "http://127.0.0.1:3030/v1")
GITHUB_COPILOT_API_KEY = getenv("GITHUB_COPILOT_API_KEY", "optional")
NVIDIA_API_KEY = getenv("NVIDIA_API_KEY", "")

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
RUNTIME_ENV = getenv("RUNTIME_ENV", "dev")

# ---------------------------------------------------------------------------
# AUT Configuration (Application Under Test)
# ---------------------------------------------------------------------------
AUT_BASE_URL = getenv("AUT_BASE_URL", "https://lokeshsharma99.github.io/GDS-Demo-App/")
AUT_AUTH_USER = getenv("AUT_AUTH_USER", "")
AUT_AUTH_PASS = getenv("AUT_AUTH_PASS", "")

# AUT GitHub repo (GDS-Demo-App) — used by GitHub MCP tools
AUT_GITHUB_OWNER = getenv("AUT_GITHUB_OWNER", "lokeshsharma99")
AUT_GITHUB_REPO = getenv("AUT_GITHUB_REPO", "GDS-Demo-App")
AUT_GITHUB_REPO_FULL = f"{AUT_GITHUB_OWNER}/{AUT_GITHUB_REPO}"
AUT_PRODUCTION_URL = getenv("AUT_PRODUCTION_URL", "https://lokeshsharma99.github.io/GDS-Demo-App/")
AUT_ALLURE_REPORT_URL = getenv("AUT_ALLURE_REPORT_URL", "https://lokeshsharma99.github.io/GDS-Demo-App/allure-report/")
AUT_GITHUB_PROJECT_URL = getenv("AUT_GITHUB_PROJECT_URL", "https://github.com/users/lokeshsharma99/projects/6/views/1")
AUT_SONARCLOUD_URL = getenv("AUT_SONARCLOUD_URL", "https://sonarcloud.io/summary/overall?id=lokeshsharma99_GDS-Demo-App&branch=main")
AUT_WIKI_DOMAIN_KNOWLEDGE_URL = "https://github.com/lokeshsharma99/GDS-Demo-App/wiki/Domain-Knowledge"
AUT_WIKI_WIREFRAMES_URL = "https://github.com/lokeshsharma99/GDS-Demo-App/wiki/Wireframes"

# ---------------------------------------------------------------------------
# Jira / ADO Integration
# ---------------------------------------------------------------------------
JIRA_URL = getenv("JIRA_URL", "")
JIRA_USERNAME = getenv("JIRA_USERNAME", "")
JIRA_API_TOKEN = getenv("JIRA_API_TOKEN", "")
AZURE_DEVOPS_URL = getenv("AZURE_DEVOPS_URL", "")
AZURE_DEVOPS_EMAIL = getenv("AZURE_DEVOPS_EMAIL", "")
AZURE_DEVOPS_PAT = getenv("AZURE_DEVOPS_PAT", "")
AZURE_DEVOPS_PROJECT = getenv("AZURE_DEVOPS_PROJECT", "")

# ---------------------------------------------------------------------------
# Atlassian MCP (Jira + Confluence via Rovo MCP Server)
# ---------------------------------------------------------------------------
ATLASSIAN_URL = getenv("ATLASSIAN_URL", "")
ATLASSIAN_EMAIL = getenv("ATLASSIAN_EMAIL", "")
ATLASSIAN_API_TOKEN = getenv("ATLASSIAN_API_TOKEN", "")
ATLASSIAN_CLOUD_ID = getenv("ATLASSIAN_CLOUD_ID", "")
ATLASSIAN_JIRA_PROJECT = getenv("ATLASSIAN_JIRA_PROJECT", "")
ATLASSIAN_CONFLUENCE_SPACE = getenv("ATLASSIAN_CONFLUENCE_SPACE", "")

# ---------------------------------------------------------------------------
# Optional tools
# ---------------------------------------------------------------------------
PARALLEL_API_KEY = getenv("PARALLEL_API_KEY", "cV5e6HkHA61snK9NIHqBybVfgGnVKSyODOP-yjqB")

# ---------------------------------------------------------------------------
# Agentic Judge Quality Gate
# ---------------------------------------------------------------------------
AUTO_APPROVE_CONFIDENCE_THRESHOLD: float = 0.90  # Judge auto-approves at ≥ 90%


def get_parallel_tools(**kwargs) -> list:  # type: ignore[type-arg]
    """Return ParallelTools if PARALLEL_API_KEY is set, else empty list."""
    if PARALLEL_API_KEY:
        from agno.tools.parallel import ParallelTools

        return [ParallelTools(**kwargs)]
    return []
