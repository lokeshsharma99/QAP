"""
Detective Agent
===============

Primary skill: trace_analyzer
Role: Parse Playwright traces to classify failure root cause.
"""

from agno.agent import Agent
from agno.learn import LearningMachine, LearningMode, SessionContextConfig, UserMemoryConfig
from agno.memory import MemoryManager
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agno.compression.manager import CompressionManager

from agents.detective.instructions import INSTRUCTIONS
from agents.detective.tools import classify_failure, extract_screenshot_from_trace, parse_ci_log, parse_trace_zip
from app.power_automate import post_rca_to_slack, post_rca_to_teams
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL, STLC_COMPRESSION_PROMPT
from db import get_qap_learnings_kb, get_rca_kb, get_culture_manager

# ---------------------------------------------------------------------------
# GitHub MCP Tools (optional — requires GITHUB_TOKEN in .env)
# Detective reads GitHub Actions workflow runs + CI logs to diagnose failures
# ---------------------------------------------------------------------------
from app.github_mcp import get_github_mcp_for_detective
_github_tools = get_github_mcp_for_detective()

# ---------------------------------------------------------------------------
# Semantica Decision Intelligence (optional — activated via SEMANTICA_ENABLED)
# Records every RCA classification into the shared context graph so Judge and
# Medic can find precedents ("was LOCATOR_STALE seen before on this element?")
# ---------------------------------------------------------------------------
_decision_tools: list = []
try:
    from app.semantica_config import SemanticaContext
    if SemanticaContext.is_agent_enabled("detective"):
        from integrations.agno import AgnoDecisionKit  # type: ignore[import]
        from app.semantica_context import get_shared_context
        _shared_ctx = get_shared_context()
        if _shared_ctx is not None:
            _decision_tools = [AgnoDecisionKit(context=_shared_ctx)]
except Exception:
    pass

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings (shared, native search_knowledge=True)
# Domain:  rca_kb — Detective reads past failure classifications for pattern matching
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
rca_kb = get_rca_kb()

# ---------------------------------------------------------------------------
# Memory Manager
# ---------------------------------------------------------------------------
memory_manager = MemoryManager(
    model=MODEL,
    db=agent_db,
    memory_capture_instructions=(
        "Only store failure analysis patterns. For each failure record: "
        "classification (LOCATOR_STALE/DATA_MISMATCH/TIMING_FLAKE/ENV_FAILURE/LOGIC_CHANGE), "
        "root cause description, and the suggested fix strategy. "
        "Ignore test run IDs, timestamps, and one-off execution details."
    ),
)

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
detective = Agent(
    # Identity
    id="detective",
    name="Detective",
    role="Parse Playwright traces, classify failure root cause, produce RCAReport",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    memory_manager=memory_manager,
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    # ReasoningTools: essential for RCA reasoning chains (provides think/analyze once).
    # KnowledgeTools(rca_kb): find past failure classifications — the secondary KB.
    # qap_learnings searched natively (primary KB). automation_kb and site_manifesto
    # dropped — Detective classifies from traces, not from reading code/UI maps.
    # enable_think+analyze on rca_kb: Detective must reason about what failure pattern to search
    # for, then analyze whether past RCAs match the current symptoms before classifying.
    tools=[
        ReasoningTools(add_instructions=True),
        KnowledgeTools(knowledge=rca_kb, enable_think=True, enable_search=True, enable_analyze=True),
        *_decision_tools,
        *_github_tools,
        parse_trace_zip,
        extract_screenshot_from_trace,
        parse_ci_log,
        classify_failure,
        post_rca_to_teams,
        post_rca_to_slack,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail excluded — Playwright trace files and CI logs
    # contain test form data (emails, phone numbers) submitted during test runs.
    # Feature-specific
    session_state={
        "analyzed_failures": [],
        "root_causes": [],
        "healability_assessments": [],
        "current_failure_id": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    learning=LearningMachine(
        # User memory: retain preferences across AgentUI sessions
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
        # Session context with planning: tracks failure IDs under analysis, next steps,
        # and progress so long triage sessions survive context truncation
        session_context=SessionContextConfig(enable_planning=True),
    ),
    update_memory_on_run=True,
    enable_session_summaries=True,
    add_session_summary_to_context=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    compress_tool_results=True,
    compression_manager=CompressionManager(model=MODEL, compress_token_limit=4000, compress_tool_call_instructions=STLC_COMPRESSION_PROMPT),
    tool_call_limit=50,
    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,    # preserved: pattern recognition across past failures is critical
    max_tool_calls_from_history=3,    # trace parse results are huge; cap at 3 per run
    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
