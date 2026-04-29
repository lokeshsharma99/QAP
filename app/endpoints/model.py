"""
Model Switch API
================
Allows the frontend control plane to switch the active LLM provider and model
at runtime without restarting the container.

Supports: Kilo AI, NVIDIA NIM, GitHub Copilot, OpenAI, Ollama, OpenRouter
"""

import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/model", tags=["model"])

# ---------------------------------------------------------------------------
# Provider catalogue
# ---------------------------------------------------------------------------

PROVIDER_CATALOGUE: dict = {
    "kilo": {
        "name": "Kilo AI",
        "description": "Kilo AI OpenRouter proxy — free tier available",
        "base_url": "https://api.kilo.ai/api/openrouter/v1",
        "models": [
            {"id": "kilo-auto/free", "label": "Kilo Auto (Free)"},
            {"id": "kilo-auto/balanced", "label": "Kilo Auto (Balanced)"},
        ],
        "default_model": "kilo-auto/free",
        "requires_key": False,
        "key_env": "KILO_API_KEY",
    },
    "nvidia": {
        "name": "NVIDIA NIM",
        "description": "NVIDIA AI Foundation models via NIM API",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "models": [
            {"id": "qwen/qwen3-coder-480b-a35b-instruct", "label": "Qwen3 Coder 480B"},
            {"id": "meta/llama-3.3-70b-instruct", "label": "Llama 3.3 70B"},
            {"id": "meta/llama-3.1-8b-instruct", "label": "Llama 3.1 8B"},
            {"id": "nvidia/llama-3.1-nemotron-70b-instruct", "label": "Nemotron 70B"},
            {"id": "microsoft/phi-3-medium-128k-instruct", "label": "Phi-3 Medium 128K"},
            {"id": "google/gemma-2-27b-it", "label": "Gemma 2 27B"},
        ],
        "default_model": "qwen/qwen3-coder-480b-a35b-instruct",
        "requires_key": True,
        "key_env": "NVIDIA_API_KEY",
    },
    "github_copilot": {
        "name": "GitHub Copilot",
        "description": "GitHub Copilot local proxy (127.0.0.1:3030)",
        "base_url": "http://127.0.0.1:3030/v1",
        "models": [
            {"id": "gpt-4o", "label": "GPT-4o"},
            {"id": "gpt-4o-mini", "label": "GPT-4o Mini"},
            {"id": "o1-preview", "label": "o1 Preview"},
            {"id": "claude-3.5-sonnet", "label": "Claude 3.5 Sonnet"},
        ],
        "default_model": "gpt-4o",
        "requires_key": False,
        "key_env": "GITHUB_COPILOT_API_KEY",
    },
    "openai": {
        "name": "OpenAI",
        "description": "OpenAI GPT models",
        "base_url": "https://api.openai.com/v1",
        "models": [
            {"id": "gpt-4o", "label": "GPT-4o"},
            {"id": "gpt-4o-mini", "label": "GPT-4o Mini"},
            {"id": "gpt-4-turbo", "label": "GPT-4 Turbo"},
            {"id": "o1", "label": "o1"},
        ],
        "default_model": "gpt-4o",
        "requires_key": True,
        "key_env": "OPENAI_API_KEY",
    },
    "ollama": {
        "name": "Ollama",
        "description": "Local Ollama instance (host.docker.internal:11434)",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1"),
        "models": [
            {"id": "llama3.2", "label": "Llama 3.2"},
            {"id": "llama3.1:8b", "label": "Llama 3.1 8B"},
            {"id": "qwen2.5:7b", "label": "Qwen 2.5 7B"},
            {"id": "deepseek-r1:7b", "label": "DeepSeek R1 7B"},
        ],
        "default_model": os.getenv("OLLAMA_MODEL", "llama3.2"),
        "requires_key": False,
        "key_env": None,
    },
    "openrouter": {
        "name": "OpenRouter",
        "description": "OpenRouter — access all frontier models",
        "base_url": "https://openrouter.ai/api/v1",
        "models": [
            {"id": "openai/gpt-4o", "label": "GPT-4o"},
            {"id": "anthropic/claude-3.5-sonnet", "label": "Claude 3.5 Sonnet"},
            {"id": "google/gemini-pro-1.5", "label": "Gemini Pro 1.5"},
            {"id": "mistralai/mistral-large", "label": "Mistral Large"},
        ],
        "default_model": "openai/gpt-4o",
        "requires_key": True,
        "key_env": "OPENROUTER_API_KEY",
    },
}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class ModelSwitchRequest(BaseModel):
    provider: str
    model_id: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/providers")
async def get_providers():
    """Return the provider catalogue plus the currently active provider/model."""
    return {
        "providers": PROVIDER_CATALOGUE,
        "active_provider": os.getenv("ACTIVE_PROVIDER", "kilo"),
        "active_model": os.getenv("ACTIVE_MODEL", "kilo-auto/free"),
        "active_base_url": os.getenv("ACTIVE_BASE_URL", "https://api.kilo.ai/api/openrouter/v1"),
    }


@router.get("/active")
async def get_active_model():
    """Return the currently active provider and model."""
    return {
        "provider": os.getenv("ACTIVE_PROVIDER", "kilo"),
        "model": os.getenv("ACTIVE_MODEL", "kilo-auto/free"),
        "base_url": os.getenv("ACTIVE_BASE_URL", "https://api.kilo.ai/api/openrouter/v1"),
    }


@router.post("/switch")
async def switch_model(req: ModelSwitchRequest):
    """Switch the active model/provider and update all running agents."""
    import app.settings as settings  # late import to avoid circular

    if req.provider not in PROVIDER_CATALOGUE:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {req.provider}")

    provider_info = PROVIDER_CATALOGUE[req.provider]
    effective_base_url = req.base_url or provider_info["base_url"]

    # Persist to env vars
    os.environ["ACTIVE_PROVIDER"] = req.provider
    os.environ["ACTIVE_MODEL"] = req.model_id
    os.environ["ACTIVE_BASE_URL"] = effective_base_url

    # Persist API key to the provider-specific env var
    key_env = provider_info.get("key_env")
    effective_key: str = "optional"
    if req.api_key and key_env:
        os.environ[key_env] = req.api_key
        effective_key = req.api_key
    elif key_env:
        effective_key = os.getenv(key_env, "optional")

    # Build the new Agno model instance
    new_model = _build_model(req.provider, req.model_id, effective_base_url, effective_key)

    # Update the global MODEL reference in app.settings
    settings.MODEL = new_model

    # Best-effort: propagate to all registered agents and teams
    updated = 0
    try:
        from app.main import agent_os  # type: ignore[attr-defined]

        for agent in agent_os.agents or []:
            agent.model = new_model
            updated += 1
        for team in agent_os.teams or []:
            team.model = new_model
            updated += 1
    except Exception:
        pass

    return {
        "status": "ok",
        "provider": req.provider,
        "provider_name": provider_info["name"],
        "model": req.model_id,
        "base_url": effective_base_url,
        "agents_updated": updated,
        "message": f"Switched to {provider_info['name']} / {req.model_id}",
    }


# ---------------------------------------------------------------------------
# Model builder
# ---------------------------------------------------------------------------


def _build_model(provider: str, model_id: str, base_url: str, api_key: str = "optional"):
    """Construct an Agno model instance for the given provider.

    All providers use OpenRouter (extends OpenAI client) since they all expose
    OpenAI-compatible endpoints. The base_url determines which backend is called.
    """
    from agno.models.openrouter import OpenRouter

    return OpenRouter(id=model_id, base_url=base_url, api_key=api_key, max_tokens=None)
