"""
CI Log Analyzer Agent
=====================

Analyzes Azure DevOps CI pipeline logs, performs RCA with learning/memory,
and creates Azure DevOps tickets after HITL approval.
Primary Skill: rca_analysis
"""

import logging

from agno.approval import approval
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
from agents.ci_log_analyzer.instructions import INSTRUCTIONS
from agents.ci_log_analyzer.tools import (
    create_work_item,
    get_pipeline_runs,
)
from app.settings import MODEL, agent_db
from db.session import get_rca_knowledge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Create Knowledge Base
# ---------------------------------------------------------------------------
# RCA-specific knowledge base for storing historical RCA learnings
rca_knowledge = get_rca_knowledge()

if rca_knowledge is not None:
    logger.info("CI Log Analyzer: RCA knowledge base loaded")
else:
    logger.warning("CI Log Analyzer: RCA knowledge base is None - historical RCA unavailable")

# ---------------------------------------------------------------------------
# Build Tools List
# ---------------------------------------------------------------------------
tools = [
    ReasoningTools(
        enable_think=True,
        enable_analyze=True,
        add_instructions=True,
        add_few_shot=True,
    ),
    get_pipeline_runs,
    create_work_item,
]

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
ci_log_analyzer = SemanticaAgent(
    # Identity
    id="ci_log_analyzer",
    name="CI Log Analyzer",
    role="Analyze Azure DevOps CI pipeline logs, perform RCA with historical knowledge, create work items after HITL approval",

    # Model
    model=MODEL,

    # Data
    db=agent_db,
    knowledge=rca_knowledge if rca_knowledge else None,
    search_knowledge=rca_knowledge is not None,

    # Capabilities
    tools=tools,

    # Instructions
    instructions=INSTRUCTIONS,

    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        pii_detection_guardrail,
        prompt_injection_guardrail,
    ],

    # Memory
    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,
    update_memory_on_run=True,
    enable_session_summaries=False,  # Disabled to reduce context window

    # Context
    add_datetime_to_context=True,
    add_history_to_context=False,  # Disabled to prevent context overflow
    read_chat_history=False,  # Disabled to prevent context overflow
    num_history_runs=0,

    # Output
    markdown=True,
)
