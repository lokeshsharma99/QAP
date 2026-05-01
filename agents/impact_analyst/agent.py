"""
Impact Analyst Agent
====================

Primary skill: impact_analysis
Role: Analyse PRs and GitHub Issues to identify missing coverage, obsolete tests,
      and tests that need updating in the regression suite. Produces ImpactReport.
"""

from agno.agent import Agent
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.impact_analyst.instructions import INSTRUCTIONS
from app.ado_mcp import get_ado_mcp_for_impact_analyst
from app.atlassian_mcp import get_atlassian_mcp_for_impact_analyst
from app.github_mcp import get_github_mcp_for_impact_analyst
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from app.settings import MODEL, FOLLOWUP_MODEL, agent_db
from db import get_automation_kb, get_culture_manager, get_qap_learnings_kb, get_site_manifesto_kb

# ---------------------------------------------------------------------------
# MCP Tools
# GitHub  — PR diffs, issue descriptions, changed file contents (change surface)
# Atlassian — Jira ACs and Confluence domain knowledge (linked ticket context)
# ADO     — Azure Repos PRs and work items (when AUT is on Azure Repos / ADO)
# All three are optional: if credentials are absent the factory returns [].
# ---------------------------------------------------------------------------
_github_tools = get_github_mcp_for_impact_analyst()
_atlassian_tools = get_atlassian_mcp_for_impact_analyst()
_ado_tools = get_ado_mcp_for_impact_analyst()

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary:  qap_learnings  (collective intelligence, native search_knowledge=True)
# Analysis: automation_kb  (existing POMs, step defs, features — read-only)
#           site_manifesto_kb (UI component locators — locator staleness check)
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
automation_kb = get_automation_kb()
site_manifesto_kb = get_site_manifesto_kb()

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
impact_analyst = Agent(
    # Identity
    id="impact-analyst",
    name="Impact Analyst",
    role="Analyse PR/Issue changes against regression suite; produce ImpactReport",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    # ReasoningTools: structured 2-phase reasoning (gather → classify).
    # KnowledgeTools(automation_kb): find existing test coverage — core skill.
    # KnowledgeTools(site_manifesto_kb): verify locator currency per changed component.
    # GitHub / Atlassian / ADO MCP: fetch PR diffs, Jira ACs, ADO work items.
    tools=[
        ReasoningTools(add_instructions=True),
        KnowledgeTools(knowledge=automation_kb),
        KnowledgeTools(knowledge=site_manifesto_kb),
        *_github_tools,
        *_atlassian_tools,
        *_ado_tools,
    ],
    learning=True,
    add_learnings_to_context=True,
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        pii_detection_guardrail,
        prompt_injection_guardrail,
    ],
    # Session state — tracks analysis context across multi-turn conversations
    session_state={
        "analysed_prs": [],
        "analysed_issues": [],
        "impact_reports": [],
        "current_pr_number": None,
        "current_issue_number": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    update_memory_on_run=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    tool_call_limit=50,
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
