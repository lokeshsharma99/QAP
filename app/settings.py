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
# Alternative / fast models
# Set MODEL_PROVIDER env var to switch all agents without editing agent files.
#
#   MODEL_PROVIDER=nvidia      → qwen/qwen3-coder-480b-a35b-instruct via NVIDIA NIM (DEFAULT)
#   MODEL_PROVIDER=kilo        → kilo-auto/free (free tier via Kilo AI)
#   MODEL_PROVIDER=kilo_paid   → kilo-auto/balanced (faster, requires KILO_API_KEY)
#   MODEL_PROVIDER=gemini      → google/gemini-2.5-flash (fastest, requires GOOGLE_API_KEY)
#   MODEL_PROVIDER=gpt4o_mini  → openai/gpt-4o-mini (fast + cheap, requires OPENAI_API_KEY)
#   MODEL_PROVIDER=haiku        → anthropic/claude-3.5-haiku (fast, requires ANTHROPIC_API_KEY)
#
# Benchmarks observed in this deployment (avg TTFT on ~19k token contexts):
#   nvidia NIM         → ~1-3s TTFT, 200+ t/s (qwen3-coder-480b, direct NVIDIA API)
#   kilo-auto/free     → avg 23s TTFT, 10-61 t/s, spikes to 94s (shared NVIDIA NIM queue)
#   kilo-auto/balanced → ~3-8s TTFT (estimated, same infra, priority queue)
#   gemini-2.5-flash   → ~1-3s TTFT, 200-500 t/s, excellent tool calling
#   gpt-4o-mini        → ~0.5-2s TTFT, 200+ t/s
# ---------------------------------------------------------------------------
_MODEL_PROVIDER = getenv("MODEL_PROVIDER", "nvidia").lower()

_GOOGLE_KEY = getenv("GOOGLE_API_KEY", "")
_OPENAI_KEY = getenv("OPENAI_API_KEY", "")
_ANTHROPIC_KEY = getenv("ANTHROPIC_API_KEY", "")
_NVIDIA_KEY = getenv("NVIDIA_API_KEY", "")
_NVIDIA_MODEL = getenv("NVIDIA_MODEL", "qwen/qwen3-coder-480b-a35b-instruct")
_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

if _MODEL_PROVIDER == "nvidia" and _NVIDIA_KEY:
    from agno.models.openai import OpenAIChat
    MODEL = OpenAIChat(
        id=_NVIDIA_MODEL,
        base_url=_NVIDIA_BASE_URL,
        api_key=_NVIDIA_KEY,
        max_tokens=4096,
    )
    FOLLOWUP_MODEL = OpenAIChat(
        id=_NVIDIA_MODEL,
        base_url=_NVIDIA_BASE_URL,
        api_key=_NVIDIA_KEY,
        max_tokens=2048,
        supports_native_structured_outputs=False,
    )
elif _MODEL_PROVIDER == "gemini" and _GOOGLE_KEY:
    from agno.models.google import Gemini
    MODEL = Gemini(id="gemini-2.0-flash", api_key=_GOOGLE_KEY)
    FOLLOWUP_MODEL = Gemini(id="gemini-2.0-flash", api_key=_GOOGLE_KEY)
elif _MODEL_PROVIDER == "gpt4o_mini" and _OPENAI_KEY:
    from agno.models.openai import OpenAIChat
    MODEL = OpenAIChat(id="gpt-4o-mini", api_key=_OPENAI_KEY)
    FOLLOWUP_MODEL = OpenAIChat(id="gpt-4o-mini", api_key=_OPENAI_KEY, max_tokens=2048)
elif _MODEL_PROVIDER == "haiku" and _ANTHROPIC_KEY:
    from agno.models.anthropic import Claude
    MODEL = Claude(id="claude-3-5-haiku-20241022", api_key=_ANTHROPIC_KEY)
    FOLLOWUP_MODEL = Claude(id="claude-3-5-haiku-20241022", api_key=_ANTHROPIC_KEY, max_tokens=2048)
elif _MODEL_PROVIDER in ("kilo_paid", "kilo") and _KILO_KEY != "anonymous":
    # Already set above as kilo-auto/balanced — no change needed
    pass
# else: fall through — MODEL already set to kilo-auto/free above

# ---------------------------------------------------------------------------
# Additional LLM provider credentials (used by /model/switch endpoint)
# ---------------------------------------------------------------------------
GITHUB_COPILOT_BASE_URL = getenv("GITHUB_COPILOT_BASE_URL", "http://127.0.0.1:3030/v1")
GITHUB_COPILOT_API_KEY = getenv("GITHUB_COPILOT_API_KEY", "optional")
NVIDIA_API_KEY = _NVIDIA_KEY

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
RUNTIME_ENV = getenv("RUNTIME_ENV", "dev")

# ---------------------------------------------------------------------------
# STLC Context Compression Prompt
# Shared across ALL agents — overrides Agno's generic OpenAI example prompt.
# ---------------------------------------------------------------------------
from textwrap import dedent as _dedent  # noqa: E402

STLC_COMPRESSION_PROMPT = _dedent("""\
    You are compressing tool call results for a Software Testing Life Cycle (STLC)
    AI system. Your goal: preserve every critical STLC fact while eliminating all noise.

    ALWAYS PRESERVE:
    • Test artefact identifiers: feature file paths, step names, POM class/method names,
      locators (data-testid, role, text selectors), Cucumber step text
    • Defect and ticket IDs: Jira/ADO ticket numbers, PR numbers, commit SHAs
    • RCA classifications: LOCATOR_STALE, DATA_MISMATCH, TIMING_FLAKE, ENV_FAILURE, LOGIC_CHANGE
    • Playwright error messages verbatim (first 150 chars): "Locator not found", "Timeout exceeded", etc.
    • File paths, line numbers, function names related to the failing or changed code
    • Acceptance Criteria IDs (AC-001, AC-002, …) and their pass/fail status
    • Environment and AUT info: base URL, browser, OS, screenshot/trace references
    • Confidence scores, threshold results (e.g., "confidence: 0.93 → APPROVED")
    • SQL seed queries, API mock endpoints, test user credentials structure (mask PII)
    • Git branch names, merge targets, CI pipeline names and stage names

    COMPRESS TO ESSENTIALS:
    • Long stack traces → file + line + error type only
    • Full HTML/accessibility trees → relevant locator + element role + text only
    • Verbose API JSON responses → relevant fields only
    • Long requirement descriptions → acceptance criteria bullet points only

    REMOVE ENTIRELY:
    • Generic introductions, filler, hedging language
    • Repeated boilerplate (e.g., repeated import blocks, license headers)
    • Non-STLC content (marketing text, unrelated logs)
    • Duplicate information already captured earlier in context

    EXAMPLE:
    Input: "The Playwright test 'Login with valid credentials' failed on line 47 of
    pages/LoginPage.ts. The error was: TimeoutError: Locator
    '[data-testid=\\"login-submit-btn\\"]' not found after 30000ms. Screenshot saved to
    test-results/screenshots/login-fail.png. The test was last passing on commit
    abc1234. The page title was 'Sign In — GDS Demo App'. Browser: Chromium 123."

    Output: "FAIL Login valid creds — LoginPage.ts:47 TimeoutError data-testid=login-submit-btn
    (30s); last green: abc1234; screenshot: login-fail.png; Chromium 123"

    Be concise. Retain every locator, ID, file path, and error detail.
    """)


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
