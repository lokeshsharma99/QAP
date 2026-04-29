"""
Detective Agent
===============

Primary skill: trace_analyzer
Role: Parse Playwright traces to classify failure root cause.
"""

from agno.agent import Agent
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.detective.instructions import INSTRUCTIONS
from agents.detective.tools import classify_failure, extract_screenshot_from_trace, parse_ci_log, parse_trace_zip
from app.settings import MODEL, agent_db
from db import get_automation_kb, get_qap_learnings_kb, get_rca_kb, get_site_manifesto_kb

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
# Primary: qap_learnings (shared)
# Domain:  rca_kb      — Detective WRITES failure classifications here
#          automation_kb  — Detective reads code to understand what broke
#          site_manifesto — Detective checks if UI changed
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
rca_kb = get_rca_kb()
automation_kb = get_automation_kb()
site_manifesto_kb = get_site_manifesto_kb()

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
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    tools=[
        ReasoningTools(add_instructions=True),
        KnowledgeTools(knowledge=qap_learnings_kb),
        KnowledgeTools(knowledge=rca_kb),
        KnowledgeTools(knowledge=automation_kb),
        KnowledgeTools(knowledge=site_manifesto_kb),
        *_decision_tools,
        *_github_tools,
        parse_trace_zip,
        extract_screenshot_from_trace,
        parse_ci_log,
        classify_failure,
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
        "analyzed_failures": [],
        "root_causes": [],
        "healability_assessments": [],
        "current_failure_id": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    enable_agentic_memory=True,
    update_memory_on_run=True,
    enable_session_summaries=True,
    add_session_summary_to_context=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    compress_tool_results=True,
    tool_call_limit=50,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
