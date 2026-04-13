"""
Settings
========

Shared configuration for Quality Autopilot.
All agents, teams, and workflows import from here.
"""

from os import getenv

from agno.models.openai import OpenAILike

from db import get_postgres_db

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
try:
    agent_db = get_postgres_db()
except Exception:
    agent_db = None

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
# Primary model: Ollama Cloud (OpenAI-compatible endpoint)
OLLAMA_API_KEY = getenv("OLLAMA_API_KEY", "")
OLLAMA_BASE_URL = getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
OLLAMA_MODEL_ID = getenv("OLLAMA_MODEL", "minimax-m2.7:cloud")

# Available Ollama Cloud models
OLLAMA_MODELS = getenv("OLLAMA_MODELS", "minimax-m2.7:cloud,glm-5.1:cloud,qwen3-coder-next").split(",")

MODEL = OpenAILike(
    id=OLLAMA_MODEL_ID,
    api_key=OLLAMA_API_KEY,
    base_url=f"{OLLAMA_BASE_URL}/v1",
)

# Smaller/faster model for lightweight tasks
MODEL_MINI = OpenAILike(
    id=OLLAMA_MODEL_ID,
    api_key=OLLAMA_API_KEY,
    base_url=f"{OLLAMA_BASE_URL}/v1",
)

def get_model(model_id: str | None = None) -> OpenAILike:
    """Get a model instance by ID.

    Args:
        model_id: Optional model ID. If not provided, uses the default OLLAMA_MODEL_ID.

    Returns:
        Configured OpenAILike model instance.
    """
    if model_id is None:
        model_id = OLLAMA_MODEL_ID
    return OpenAILike(
        id=model_id,
        api_key=OLLAMA_API_KEY,
        base_url=f"{OLLAMA_BASE_URL}/v1",
    )

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
RUNTIME_ENV = getenv("RUNTIME_ENV", "dev")

# ---------------------------------------------------------------------------
# Autonomous Mode Configuration
# ---------------------------------------------------------------------------
AUTONOMOUS_MODE = getenv("AUTONOMOUS_MODE", "false").lower() in ["true", "1", "yes"]
AUTO_APPROVE_CONFIDENCE_THRESHOLD = float(getenv("AUTO_APPROVE_CONFIDENCE_THRESHOLD", "90.0"))

# ---------------------------------------------------------------------------
# AUT Configuration
# ---------------------------------------------------------------------------
AUT_BASE_URL = getenv("AUT_BASE_URL", "https://gds-demo-app.vercel.app/")
AUT_AUTH_USER = getenv("AUT_AUTH_USER", "")
AUT_AUTH_PASS = getenv("AUT_AUTH_PASS", "")

# ---------------------------------------------------------------------------
# GitHub Configuration
# ---------------------------------------------------------------------------
GITHUB_TOKEN = getenv("GITHUB_TOKEN", "")
GITHUB_REPO = getenv("GITHUB_REPO", "")
GITHUB_OWNER = getenv("GITHUB_OWNER", "")
GITHUB_DEFAULT_BRANCH = getenv("GITHUB_DEFAULT_BRANCH", "main")
