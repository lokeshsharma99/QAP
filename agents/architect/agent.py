"""
Architect Agent
===============

Primary skill: semantic_search
Role: Parse requirements, query KB for impact, produce RequirementContext (Execution Plan).
"""

from agno.agent import Agent
from agno.memory import MemoryManager
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.user_control_flow import UserControlFlowTools

from agents.architect.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db import get_qap_learnings_kb, get_site_manifesto_kb

# ---------------------------------------------------------------------------
# GitHub MCP Tools (optional — requires GITHUB_TOKEN in .env)
# Architect reads GitHub Issues as requirement source + Wiki for domain context
# ---------------------------------------------------------------------------
from app.ado_mcp import get_ado_mcp_for_architect
from app.atlassian_mcp import get_atlassian_mcp_for_architect
from app.github_mcp import get_github_mcp_for_architect
_github_tools = get_github_mcp_for_architect()

# ---------------------------------------------------------------------------
# Azure DevOps MCP Tools (requires AZURE_DEVOPS_URL + AZURE_DEVOPS_PAT in .env)
# Domains: core, work-items — reads ADO work items as alternative requirement source
# ---------------------------------------------------------------------------
_ado_tools = get_ado_mcp_for_architect()

# ---------------------------------------------------------------------------
# Atlassian MCP Tools (requires ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN in .env)
# Reads Jira issues (ACs, descriptions) and Confluence docs as requirements
# ---------------------------------------------------------------------------
_atlassian_tools = get_atlassian_mcp_for_architect()

# ---------------------------------------------------------------------------
# Semantica Context Graph Toolkit (optional — activated via SEMANTICA_ENABLED)
# Architect uses context graphs to build requirement-to-POM traceability:
# - Node: Jira ticket → links to affected PageObjects → links to Gherkin specs
# - Traceability graph shows which tests cover which acceptance criteria
# - KG dedup ensures the same POM isn't listed twice under different names
# ---------------------------------------------------------------------------
_kg_tools: list = []
try:
    from app.semantica_config import SemanticaContext
    if SemanticaContext.is_agent_enabled("architect"):
        from integrations.agno import AgnoKGToolkit  # type: ignore[import]
        from app.semantica_context import get_shared_context
        _shared_ctx = get_shared_context()
        if _shared_ctx is not None:
            _kg_tools = [AgnoKGToolkit(context=_shared_ctx)]
except Exception:
    pass

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings (shared collective intelligence, native search_knowledge=True)
# Domain:  site_manifesto — Architect reads page/component map to identify affected POMs
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
site_manifesto_kb = get_site_manifesto_kb()

# ---------------------------------------------------------------------------
# Memory Manager
# ---------------------------------------------------------------------------
memory_manager = MemoryManager(
    db=agent_db,
    memory_capture_instructions=(
        "Only store requirement analysis patterns: the feature domain, "
        "commonly affected Page Objects for that domain, and reusable "
        "acceptance criteria patterns. Ignore ticket IDs, sprint names, "
        "and one-off implementation details."
    ),
)

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
architect = Agent(
    # Identity
    id="architect",
    name="Architect",
    role="Analyze requirements, query KB for impact, produce Execution Plan",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    memory_manager=memory_manager,
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    # ReasoningTools: core reasoning for requirement analysis (provides think/analyze).
    # KnowledgeTools(site_manifesto_kb): query live UI map to identify affected pages.
    # automation_kb searched natively via search_knowledge=True (qap_learnings is primary KB).
    tools=[
        ReasoningTools(add_instructions=True),
        UserControlFlowTools(),
        KnowledgeTools(knowledge=site_manifesto_kb),
        *_kg_tools,
        *_github_tools,
        *_ado_tools,
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
        "analyzed_requirements": [],
        "affected_pages": [],
        "execution_plan": None,
        "current_requirement_id": None,
    },
    enable_agentic_state=True,
    add_session_state_to_context=True,
    # Memory
    update_memory_on_run=True,
    enable_session_summaries=True,
    add_session_summary_to_context=True,
    search_past_sessions=True,
    num_past_sessions_to_search=3,
    tool_call_limit=50,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
    followups=True,
    num_followups=3,
)
