"""
Agent Config API
================
Allows the frontend to read and update individual agent (or team) configuration
at runtime without restarting the container.

Mutable fields per run:
  name, instructions, model, num_history_runs, add_history_to_context,
  session_state, add_session_state_to_context, enable_agentic_state,
  enable_agentic_memory, update_memory_on_run
"""

import json
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(tags=["agent-config"])


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


class AgentConfigUpdate(BaseModel):
    name: Optional[str] = None
    instructions: Optional[str] = None
    model_id: Optional[str] = None
    model_provider: Optional[str] = None
    model_base_url: Optional[str] = None
    model_api_key: Optional[str] = None
    num_history_runs: Optional[int] = None
    add_history_to_context: Optional[bool] = None
    session_state: Optional[dict[str, Any]] = None
    add_session_state_to_context: Optional[bool] = None
    enable_agentic_state: Optional[bool] = None
    enable_agentic_memory: Optional[bool] = None
    update_memory_on_run: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None
    extra_config: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_agent(agent_id: str):
    """Return the live Agno Agent object registered in AgentOS, or None."""
    try:
        from app.main import agent_os  # late import to avoid circular

        for agent in agent_os.agents or []:
            if getattr(agent, "agent_id", None) == agent_id or getattr(agent, "id", None) == agent_id:
                return agent
    except Exception:
        pass
    return None


def _find_team(team_id: str):
    """Return the live Agno Team object, or None."""
    try:
        from app.main import agent_os  # late import to avoid circular

        for team in agent_os.teams or []:
            if getattr(team, "team_id", None) == team_id or getattr(team, "id", None) == team_id:
                return team
    except Exception:
        pass
    return None


def _build_model(provider: str, model_id: str, base_url: str, api_key: str = "optional"):
    """Build an Agno OpenRouter model instance (all providers expose OpenAI-compatible APIs)."""
    from agno.models.openrouter import OpenRouter

    return OpenRouter(id=model_id, base_url=base_url, api_key=api_key, max_tokens=None)


def _apply_updates(entity, req: AgentConfigUpdate) -> list[str]:
    """Apply mutable field updates to an agent or team. Returns list of changed fields."""
    changed: list[str] = []

    if req.name is not None:
        entity.name = req.name
        changed.append("name")

    if req.instructions is not None:
        entity.instructions = req.instructions
        changed.append("instructions")

    # Model swap
    if req.model_id is not None:
        # Determine base_url from catalogue or use provided
        base_url = req.model_base_url or _get_default_base_url(req.model_provider or "")
        api_key = req.model_api_key or "optional"
        entity.model = _build_model(req.model_provider or "custom", req.model_id, base_url, api_key)
        changed.append("model")

    if req.num_history_runs is not None:
        entity.num_history_runs = req.num_history_runs
        changed.append("num_history_runs")

    if req.add_history_to_context is not None:
        entity.add_history_to_context = req.add_history_to_context
        changed.append("add_history_to_context")

    if req.session_state is not None:
        entity.session_state = req.session_state
        changed.append("session_state")

    if req.add_session_state_to_context is not None:
        entity.add_session_state_to_context = req.add_session_state_to_context
        changed.append("add_session_state_to_context")

    if req.enable_agentic_state is not None:
        entity.enable_agentic_state = req.enable_agentic_state
        changed.append("enable_agentic_state")

    if req.enable_agentic_memory is not None:
        entity.enable_agentic_memory = req.enable_agentic_memory
        changed.append("enable_agentic_memory")

    if req.update_memory_on_run is not None:
        entity.update_memory_on_run = req.update_memory_on_run
        changed.append("update_memory_on_run")

    if req.metadata is not None:
        entity.metadata = req.metadata
        changed.append("metadata")

    # Apply extra_config as arbitrary attribute overrides
    if req.extra_config:
        for key, value in req.extra_config.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
                changed.append(key)

    return changed


def _get_default_base_url(provider: str) -> str:
    """Return the known base URL for a provider identifier."""
    import os

    BASES = {
        "kilo": "https://api.kilo.ai/api/openrouter/v1",
        "nvidia": "https://integrate.api.nvidia.com/v1",
        "github_copilot": "http://127.0.0.1:3030/v1",
        "openai": "https://api.openai.com/v1",
        "ollama": os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434/v1"),
        "openrouter": "https://openrouter.ai/api/v1",
    }
    return BASES.get(provider, "https://api.kilo.ai/api/openrouter/v1")


def _get_entity_snapshot(entity) -> dict:
    """Return a dict snapshot of the mutable fields for the frontend."""
    model = getattr(entity, "model", None)
    model_info: dict = {}
    if model:
        model_info = {
            "id": getattr(model, "id", ""),
            "name": getattr(model, "name", ""),
            "provider": getattr(model, "provider", ""),
            "base_url": getattr(model, "base_url", ""),
        }

    session_state_raw = getattr(entity, "session_state", {})
    if isinstance(session_state_raw, str):
        try:
            session_state_raw = json.loads(session_state_raw)
        except Exception:
            session_state_raw = {}

    return {
        "id": getattr(entity, "agent_id", None) or getattr(entity, "team_id", None) or getattr(entity, "id", ""),
        "name": getattr(entity, "name", ""),
        "instructions": getattr(entity, "instructions", ""),
        "model": model_info,
        "num_history_runs": getattr(entity, "num_history_runs", 5),
        "add_history_to_context": getattr(entity, "add_history_to_context", True),
        "session_state": session_state_raw or {},
        "add_session_state_to_context": getattr(entity, "add_session_state_to_context", False),
        "enable_agentic_state": getattr(entity, "enable_agentic_state", False),
        "enable_agentic_memory": getattr(entity, "enable_agentic_memory", True),
        "update_memory_on_run": getattr(entity, "update_memory_on_run", False),
        "metadata": getattr(entity, "metadata", {}) or {},
    }


# ---------------------------------------------------------------------------
# Routes — agent
# ---------------------------------------------------------------------------


@router.get("/agents/{agent_id}/config")
async def get_agent_config(agent_id: str):
    """Return the current mutable config for an agent."""
    agent = _find_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    return _get_entity_snapshot(agent)


@router.patch("/agents/{agent_id}/config")
async def update_agent_config(agent_id: str, req: AgentConfigUpdate):
    """Update mutable properties on a live agent."""
    agent = _find_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    changed = _apply_updates(agent, req)

    return {
        "status": "ok",
        "agent_id": agent_id,
        "changed_fields": changed,
        "snapshot": _get_entity_snapshot(agent),
    }


# ---------------------------------------------------------------------------
# Routes — team
# ---------------------------------------------------------------------------


@router.get("/teams/{team_id}/config")
async def get_team_config(team_id: str):
    """Return the current mutable config for a team."""
    team = _find_team(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")
    return _get_entity_snapshot(team)


@router.patch("/teams/{team_id}/config")
async def update_team_config(team_id: str, req: AgentConfigUpdate):
    """Update mutable properties on a live team."""
    team = _find_team(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found")

    changed = _apply_updates(team, req)

    return {
        "status": "ok",
        "team_id": team_id,
        "changed_fields": changed,
        "snapshot": _get_entity_snapshot(team),
    }
