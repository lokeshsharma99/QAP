"""
Quality Autopilot AgentOS
=========================

The main entry point for Quality Autopilot.

Run:
    python -m app.main
"""

from pathlib import Path
from pydantic import BaseModel

from agno.os import AgentOS

from agents.architect import architect
from agents.discovery import discovery
from agents.engineer import engineer
from agents.librarian import librarian
from app.registry import registry
from app.settings import OLLAMA_MODELS, OLLAMA_MODEL_ID, RUNTIME_ENV, agent_db
from workflows.automation_scaffold import automation_scaffold


class LLMSettings(BaseModel):
    """LLM provider settings."""
    provider: str
    api_key: str
    base_url: str
    model: str


# ---------------------------------------------------------------------------
# Create AgentOS
# ---------------------------------------------------------------------------
agent_os = AgentOS(
    name="Quality Autopilot",
    tracing=True,
    authorization=RUNTIME_ENV == "prd",
    db=agent_db,
    agents=[
        architect,
        discovery,
        engineer,
        librarian,
    ],
    teams=[],
    workflows=[automation_scaffold],
    registry=registry,
    config=str(Path(__file__).parent / "config.yaml"),
)

app = agent_os.get_app()


# ---------------------------------------------------------------------------
# Custom Endpoints
# ---------------------------------------------------------------------------
@app.get("/models")
def get_models():
    """Get available Ollama Cloud models."""
    return {
        "models": OLLAMA_MODELS,
        "current": OLLAMA_MODEL_ID,
    }


@app.get("/llm-settings")
def get_llm_settings():
    """Get current LLM provider settings."""
    return {
        "provider": "ollama",
        "api_key": "",  # Don't expose the actual key
        "base_url": "http://host.docker.internal:11434",
        "model": OLLAMA_MODEL_ID,
    }


@app.post("/llm-settings")
def update_llm_settings(settings: LLMSettings):
    """Update LLM provider settings (for future implementation)."""
    # This would update the environment variables or configuration
    # For now, just return success
    return {"status": "success", "message": "Settings updated"}


if __name__ == "__main__":
    agent_os.serve(
        app="app.main:app",
        reload=RUNTIME_ENV == "dev",
    )
