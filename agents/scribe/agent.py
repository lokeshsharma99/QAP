"""
Scribe Agent
============

Primary skill: gherkin_formatter
Role: Author BDD Gherkin specs from RequirementContext.
"""

from agno.agent import Agent
from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools

from agents.scribe.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db import get_qap_learnings_kb

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings — Scribe reads prior Gherkin patterns and conventions
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()

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
        CodingTools(),
        FileTools(),
        KnowledgeTools(knowledge=qap_learnings_kb),
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        PIIDetectionGuardrail(),
        PromptInjectionGuardrail(),
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
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
