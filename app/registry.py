"""
Registry
========

Shared tools, models, and database connections for AgentOS.
Models and tools are gated on their provider's API key so
the registry stays importable regardless of which keys are configured.
"""

from pathlib import Path

from agno.registry import Registry
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.reasoning import ReasoningTools

from app.settings import MODEL, agent_db


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def _get_models() -> list:
    """Build the model list."""
    return [MODEL]


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------
def _get_tools() -> list:
    """Build the tool list for Quality Autopilot."""
    tools: list = [
        CodingTools(),
        FileTools(Path("automation")),
        ReasoningTools(add_instructions=True),
    ]
    return tools


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
registry = Registry(
    tools=_get_tools(),
    models=_get_models(),
    dbs=[agent_db],
)
