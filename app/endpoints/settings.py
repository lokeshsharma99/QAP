"""
Settings API
============
Allows the frontend control plane to read and update runtime environment
variables at runtime (no container restart required).

Secrets are masked on GET to avoid leaking them over the network.
On POST /settings/update, any value equal to the mask sentinel is ignored
so existing secrets are preserved.
"""

import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])

# ---------------------------------------------------------------------------
# Allowed keys
# ---------------------------------------------------------------------------

ALLOWED_KEYS: set[str] = {
    # LLM — Ollama
    "OLLAMA_API_KEY",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_MODELS",
    # LLM — OpenAI / Anthropic / Google
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    # Integrations
    "GITHUB_TOKEN",
    "SERPER_API_KEY",
    # AUT
    "AUT_BASE_URL",
    "AUT_AUTH_USER",
    "AUT_AUTH_PASS",
    # Database
    "DB_USER",
    "DB_PASS",
    "DB_HOST",
    "DB_PORT",
    "DB_DATABASE",
    # Runtime
    "RUNTIME_ENV",
    # Jira
    "JIRA_URL",
    "JIRA_USERNAME",
    "JIRA_API_TOKEN",
    # Confluence
    "CONFLUENCE_URL",
    "CONFLUENCE_EMAIL",
    "CONFLUENCE_API_TOKEN",
    # Azure DevOps
    "AZURE_DEVOPS_URL",
    "AZURE_DEVOPS_EMAIL",
    "AZURE_DEVOPS_PAT",
    "AZURE_DEVOPS_PROJECT",
    # Model / Provider
    "ACTIVE_PROVIDER",
    "ACTIVE_MODEL",
    "ACTIVE_BASE_URL",
    "NVIDIA_API_KEY",
    "KILO_API_KEY",
    "GITHUB_COPILOT_API_KEY",
    "GITHUB_COPILOT_BASE_URL",
    "OPENROUTER_API_KEY",
}

# Keys whose values are masked in the GET response
SECRET_KEYS: set[str] = {
    "OLLAMA_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GITHUB_TOKEN",
    "SERPER_API_KEY",
    "DB_PASS",
    "AUT_AUTH_PASS",
    "JIRA_API_TOKEN",
    "CONFLUENCE_API_TOKEN",
    "AZURE_DEVOPS_PAT",
    "NVIDIA_API_KEY",
    "KILO_API_KEY",
    "GITHUB_COPILOT_API_KEY",
    "OPENROUTER_API_KEY",
}

MASK = "••••••••"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class SettingsUpdatePayload(BaseModel):
    settings: dict[str, str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
def get_settings() -> dict:
    """Return current environment settings. Secrets are masked."""
    result: dict[str, str] = {}
    for key in ALLOWED_KEYS:
        val = os.environ.get(key, "")
        if key in SECRET_KEYS and val:
            result[key] = MASK
        else:
            result[key] = val
    return result


@router.post("/update")
def update_settings(payload: SettingsUpdatePayload) -> dict:
    """
    Update os.environ at runtime.
    Any value equal to the mask sentinel is ignored to preserve existing secrets.
    """
    updated: list[str] = []
    skipped: list[str] = []

    for key, value in payload.settings.items():
        if key not in ALLOWED_KEYS:
            skipped.append(key)
            continue
        if value == MASK:
            # Client sent back the mask — don't overwrite the real secret
            skipped.append(key)
            continue
        os.environ[key] = value
        updated.append(key)

    return {
        "status": "ok",
        "updated": updated,
        "skipped": skipped,
        "count": len(updated),
    }
