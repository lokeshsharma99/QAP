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
# ---------------------------------------------------------------------------
MODEL = OpenRouter(
    id="kilo-auto/free",
    base_url="https://api.kilo.ai/api/openrouter/v1",
    max_tokens=None,
)

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
AZURE_DEVOPS_PAT = getenv("AZURE_DEVOPS_PAT", "")

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
