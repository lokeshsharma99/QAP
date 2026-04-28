"""
Detective Agent
===============

Primary skill: trace_analyzer
Role: Parse Playwright traces to classify failure root cause.
"""

from agno.agent import Agent
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.detective.instructions import INSTRUCTIONS
from agents.detective.tools import classify_failure, parse_ci_log, parse_trace_zip
from app.settings import MODEL, agent_db
from db import get_automation_kb, get_qap_learnings_kb, get_rca_kb, get_site_manifesto_kb

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
        parse_trace_zip,
        parse_ci_log,
        classify_failure,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
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
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
