"""
Architect Agent
===============

Primary skill: semantic_search
Role: Parse requirements, query KB for impact, produce RequirementContext (Execution Plan).
"""

from agno.agent import Agent
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.architect.instructions import INSTRUCTIONS
from app.settings import MODEL, agent_db
from db import get_automation_kb, get_qap_learnings_kb, get_site_manifesto_kb

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings (shared collective intelligence — all agents)
# Domain:  site_manifesto + automation (read-only — Architect queries existing POMs)
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
site_manifesto_kb = get_site_manifesto_kb()
automation_kb = get_automation_kb()

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
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    tools=[
        ReasoningTools(add_instructions=True),
        KnowledgeTools(knowledge=site_manifesto_kb),
        KnowledgeTools(knowledge=automation_kb),
    ],
    # Instructions
    instructions=INSTRUCTIONS,
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
    enable_agentic_memory=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
