"""
Observability Agent
===================

Primary skill: system_health_analysis
Role: Monitor Azure Container Apps health, surface errors, diagnose DB/model/volume failures.
"""

from agno.agent import Agent
from agno.compression.manager import CompressionManager
from agno.learn import LearningMachine, LearningMode, SessionContextConfig, UserMemoryConfig
from agno.tools.reasoning import ReasoningTools

from agents.observability.instructions import INSTRUCTIONS
from agents.observability.tools import (
    check_api_health,
    get_aca_logs,
    get_aca_revision_status,
    get_aca_env_vars,
    run_db_check,
)
from app.settings import MODEL, FOLLOWUP_MODEL, agent_db, STLC_COMPRESSION_PROMPT
from db import get_qap_learnings_kb

# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
observability = Agent(
    # Identity
    id="observability",
    name="Observability Agent",
    role="System health monitor — watches ACA logs, API health, DB connectivity, and surfaces issues",

    # Model
    model=MODEL,

    # Data
    db=agent_db,
    knowledge=qap_learnings_kb,
    search_knowledge=True,

    # Capabilities
    tools=[
        ReasoningTools(add_instructions=True),
        check_api_health,
        get_aca_logs,
        get_aca_revision_status,
        get_aca_env_vars,
        run_db_check,
    ],
    # Instructions
    instructions=INSTRUCTIONS,

    # Session state
    session_state={
        "checked_components": [],
        "active_issues": [],
        "resolved_issues": [],
        "last_health_check": None,
        "current_investigation": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,

    # Memory
    learning=LearningMachine(
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
        session_context=SessionContextConfig(enable_planning=True),
    ),
    update_memory_on_run=True,
    enable_session_summaries=True,
    add_session_summary_to_context=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,

    # Compression
    compress_tool_results=True,
    compression_manager=CompressionManager(
        model=MODEL,
        compress_token_limit=4000,
        compress_tool_call_instructions=STLC_COMPRESSION_PROMPT,
    ),
    tool_call_limit=40,

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
