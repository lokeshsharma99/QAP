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
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
from db import get_qap_learnings_kb, get_culture_manager

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings — Data Agent reads prior data patterns, writes PII/seed conventions
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

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
    update_memory_on_run=True,
    tool_call_limit=30,
    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
