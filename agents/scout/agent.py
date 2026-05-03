"""
Project Scout Agent
===================

Primary skill: unified_kb_search
Role: Answer ANY question about the project, AUT, or automation framework
      by searching all knowledge bases — Automation KB, Site Manifesto, RTM KB,
      Document Library, RCA KB, and QAP Learnings.

Does NOT write code, trigger workflows, or fetch live data.
Answers questions; routes to specialist agents for action.
"""

from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from agents.scout.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db.session import (
    get_automation_kb,
    get_document_library_kb,
    get_qap_learnings_kb,
    get_rca_kb,
    get_rtm_kb,
    get_site_manifesto_kb,
)

# ---------------------------------------------------------------------------
# Knowledge Bases — Scout reads ALL of them
# ---------------------------------------------------------------------------
_automation_kb       = get_automation_kb()
_site_manifesto_kb   = get_site_manifesto_kb()
_rtm_kb              = get_rtm_kb()
_document_library_kb = get_document_library_kb()
_rca_kb              = get_rca_kb()
_learnings_kb        = get_qap_learnings_kb()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
scout = Agent(
    # Identity
    id="scout",
    name="Project Scout",
    # Model
    model=MODEL,
    # Data — primary KB is automation (codebase), with all others as supplementary
    db=agent_db,
    knowledge=_automation_kb,
    search_knowledge=True,
    # Capabilities
    tools=[ReasoningTools(add_instructions=True)],
    learning=True,
    add_learnings_to_context=True,
    # Instructions
    instructions=INSTRUCTIONS,
    # Session state — tracks which KBs were searched this session
    session_state={
        "queries": [],
        "kbs_searched": [],
        "coverage_gaps": [],
        "current_query": None,
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
