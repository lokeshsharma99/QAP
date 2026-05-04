"""
Data Agent
==========

Primary skill: data_factory
Role: Provision test users, seed data, produce RunContext for test scenarios.
"""

from agno.agent import Agent
from agno.compression.manager import CompressionManager
from agno.learn import LearningMachine, LearningMode, UserMemoryConfig, UserProfileConfig
from agno.tools.coding import CodingTools
from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools

from agents.data_agent.instructions import INSTRUCTIONS
from agents.data_agent.tools import (
    generate_dynamic_test_user,
    get_test_data_on_demand,
    generate_run_context,
    generate_scenario_data,
    clear_data_cache,
)
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL, STLC_COMPRESSION_PROMPT
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
        FileTools(),
        KnowledgeTools(knowledge=qap_learnings_kb),
        generate_dynamic_test_user,
        get_test_data_on_demand,
        generate_run_context,
        generate_scenario_data,
        clear_data_cache,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail excluded — data_agent's core job is generating
    # synthetic PII (fake emails, phones, usernames). The guardrail would block every run.
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
    # UserProfileConfig(ALWAYS): remembers which AUT and test projects the user works on,
    # so Data Agent pre-fills domain context (base URL, roles) without re-asking.
    # UserMemoryConfig(ALWAYS): learns per-project data patterns silently — e.g.
    # "this app expects unique emails per scenario" or "admin role needs extra seed steps".
    learning=LearningMachine(
        user_profile=UserProfileConfig(mode=LearningMode.ALWAYS),
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
    ),
    update_memory_on_run=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    tool_call_limit=30,
    # Context compression — CodingTools can return verbose execution output; KB docs
    # can be long. Compress after 4 000 tokens as a safety net.
    # History kept at 5 — test data correctness requires full prior scenario context.
    compression_manager=CompressionManager(model=FOLLOWUP_MODEL, compress_token_limit=4000, compress_tool_call_instructions=STLC_COMPRESSION_PROMPT),
    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,    # preserved: data correctness depends on full prior scenario context
    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
