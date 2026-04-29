"""
Data Agent
==========

Primary skill: data_factory
Role: Provision test users, seed data, produce RunContext for test scenarios.
"""

from agno.agent import Agent
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.coding import CodingTools
from agno.tools.knowledge import KnowledgeTools

from agents.data_agent.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db import get_qap_learnings_kb

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings — Data Agent reads prior data patterns, writes PII/seed conventions
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
data_agent = Agent(
    # Identity
    id="data-agent",
    name="Data Agent",
    role="Provision test users, seed data, produce RunContext",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    tools=[
        CodingTools(),
        KnowledgeTools(knowledge=qap_learnings_kb),
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
        "generated_test_users": [],
        "generated_run_contexts": [],
        "data_cache": {},
        "current_scenario": None,
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
