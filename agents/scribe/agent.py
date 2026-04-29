"""
Scribe Agent
============

Primary skill: gherkin_formatter
Role: Author BDD Gherkin specs from RequirementContext.
"""

from agno.agent import Agent
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools

from agents.scribe.instructions import INSTRUCTIONS
from app.atlassian_mcp import get_atlassian_mcp_for_scribe
from app.settings import MODEL, agent_db
from db import get_qap_learnings_kb

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings — Scribe reads prior Gherkin patterns and conventions
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()

# ---------------------------------------------------------------------------
# Atlassian MCP Tools (requires ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN in .env)
# Scribe verifies all Jira ACs are covered and links .feature files to issues
# ---------------------------------------------------------------------------
_atlassian_tools = get_atlassian_mcp_for_scribe()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
scribe = Agent(
    # Identity
    id="scribe",
    name="Scribe",
    role="Author BDD Gherkin specs from RequirementContext",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    tools=[
        CodingTools(requires_confirmation_tools=["run_shell"]),
        FileTools(),
        KnowledgeTools(knowledge=qap_learnings_kb),
        *_atlassian_tools,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        pii_detection_guardrail,
        prompt_injection_guardrail,
    ],
    # Feature-specific
    session_state={
        "created_features": [],
        "created_scenarios": [],
        "requirement_contexts": [],
        "current_feature": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    enable_agentic_memory=True,
    learning=True,
    update_memory_on_run=True,
    enable_session_summaries=True,
    add_session_summary_to_context=True,
    tool_call_limit=50,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
