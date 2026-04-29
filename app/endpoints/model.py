"""
Model Switch API
================
Allows the frontend control plane to switch the active LLM provider and model
at runtime without restarting the container.

Supports: Kilo AI, NVIDIA NIM, GitHub Copilot, OpenAI, Ollama, OpenRouter
"""

import os
from typing import Optional

import httpx
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
        "description": "Local Ollama instance — also serves cloud models via local daemon (sign in with 'ollama signin')",
        "base_url": os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1"),
        "models": [
            {"id": m.strip(), "label": m.strip()}
            for m in os.getenv("OLLAMA_MODELS", "llama3.2,llama3.1:8b,qwen2.5:7b,deepseek-r1:7b").split(",")
            if m.strip()
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
    "ollama_cloud": {
        "name": "Ollama Cloud",
        "description": "Direct access to ollama.com cloud models via API key (OLLAMA_API_KEY)",
        "base_url": "https://ollama.com/v1",
        "models": [
            {"id": m.strip(), "label": m.strip()}
            for m in os.getenv(
                "OLLAMA_MODELS",
                "minimax-m2.7:cloud,glm-5.1:cloud,qwen3-coder-next,gpt-oss:120b-cloud",
            ).split(",")
            if m.strip()
        ],
        "default_model": os.getenv("OLLAMA_MODEL", "minimax-m2.7:cloud"),
        "requires_key": True,
        "key_env": "OLLAMA_API_KEY",
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
    requires_key = provider_info.get("requires_key", False)
    effective_key: str = "optional"

    if req.api_key and req.api_key.strip():
        # Explicit key supplied in the request — always trust it
        effective_key = req.api_key.strip()
        if key_env:
            os.environ[key_env] = effective_key
    elif key_env:
        env_val = os.getenv(key_env, "")
        if env_val:
            effective_key = env_val
        elif requires_key:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"API key required for provider '{req.provider}'. "
                    f"Set the {key_env} environment variable or supply api_key in the request."
                ),
            )
        # requires_key=False → keep "optional" (agno/OpenAI client needs a non-empty string)

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


# ---------------------------------------------------------------------------
# Live model listing
# ---------------------------------------------------------------------------


@router.get("/list/{provider}")
async def list_models(provider: str):
    """
    Return the available models for a provider.

    For Ollama: queries GET /api/tags on the running Ollama instance.
    For OpenRouter/Kilo: queries GET /models on the provider's API.
    For all others: returns the static catalogue list.

    Response: { provider, models: [{id, label}], source: "live"|"static" }
    """
    if provider not in PROVIDER_CATALOGUE:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    info = PROVIDER_CATALOGUE[provider]

    # ------------------------------------------------------------------
    # Ollama (local) — GET /api/tags  (no auth)
    # Ollama Cloud    — GET https://ollama.com/api/tags  (Bearer key)
    # ------------------------------------------------------------------
    if provider == "ollama":
        raw_base = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
        # Strip trailing /v1 to get the root API
        base = raw_base.rstrip("/").removesuffix("/v1")
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{base}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [{"id": m["name"], "label": m["name"]} for m in data.get("models", [])]
                    if models:
                        return {"provider": provider, "models": models, "source": "live"}
        except Exception:
            pass
        return {"provider": provider, "models": info["models"], "source": "static"}

    if provider == "ollama_cloud":
        api_key = os.getenv("OLLAMA_API_KEY", "")
        headers: dict = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get("https://ollama.com/api/tags", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    models = [{"id": m["name"], "label": m["name"]} for m in data.get("models", [])]
                    if models:
                        return {"provider": provider, "models": models, "source": "live"}
        except Exception:
            pass
        return {"provider": provider, "models": info["models"], "source": "static"}

    # ------------------------------------------------------------------
    # OpenRouter / Kilo — GET /models (OpenAI-compatible list endpoint)
    # ------------------------------------------------------------------
    if provider in ("openrouter", "kilo"):
        key_env = info.get("key_env") or ""
        api_key = os.getenv(key_env, "") if key_env else ""
        base_url = info["base_url"].rstrip("/")
        headers: dict = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                resp = await client.get(f"{base_url}/models", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    raw = data.get("data", [])
                    models = [
                        {"id": m["id"], "label": m.get("name", m["id"])}
                        for m in raw
                        if isinstance(m.get("id"), str)
                    ]
                    if models:
                        return {"provider": provider, "models": models, "source": "live"}
        except Exception:
            pass
        return {"provider": provider, "models": info["models"], "source": "static"}

    # ------------------------------------------------------------------
    # All other providers — return static catalogue
    # ------------------------------------------------------------------
    return {"provider": provider, "models": info["models"], "source": "static"}
