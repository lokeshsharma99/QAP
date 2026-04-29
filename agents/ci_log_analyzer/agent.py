"""
CI Log Analyzer Agent
=====================

Analyzes Azure DevOps CI pipeline logs, performs RCA with learning/memory,
and creates Azure DevOps tickets after HITL approval.
Primary Skill: rca_analysis
"""

import logging

from agno.approval import approval
from agno.learn import LearningMachine, LearningMode, SessionContextConfig, UserMemoryConfig
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
from agno.compression.manager import CompressionManager

from agents.ci_log_analyzer.instructions import INSTRUCTIONS
from agents.ci_log_analyzer.tools import (
    create_work_item,
    get_pipeline_runs,
)
from app.ado_mcp import get_ado_mcp_for_ci_log_analyzer
from app.atlassian_mcp import get_atlassian_mcp_for_ci_log_analyzer
from app.settings import MODEL, agent_db
from db.session import get_rca_kb as get_rca_knowledge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Azure DevOps MCP Tools (requires AZURE_DEVOPS_URL + AZURE_DEVOPS_PAT in .env)
# Domains: core, pipelines, work-items
# CI Log Analyzer reads ADO pipeline logs and creates work items after HITL.
# ---------------------------------------------------------------------------
_ado_tools = get_ado_mcp_for_ci_log_analyzer()

# ---------------------------------------------------------------------------
# Atlassian MCP Tools (requires ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN in .env)
# CI Log Analyzer creates Jira bugs from RCA findings after HITL approval.
# ---------------------------------------------------------------------------
_atlassian_tools = get_atlassian_mcp_for_ci_log_analyzer()

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
    *_ado_tools,
    *_atlassian_tools,
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
    learning=LearningMachine(
        # User memory: retain user preferences across sessions
        user_memory=UserMemoryConfig(mode=LearningMode.ALWAYS),
        # Session context with planning: tracks pipeline IDs analysed, steps remaining,
        # and findings so long log-analysis runs survive context truncation
        session_context=SessionContextConfig(enable_planning=True),
    ),
    update_memory_on_run=True,
    enable_session_summaries=False,  # Disabled to reduce context window
    compress_tool_results=True,
    compression_manager=CompressionManager(model=MODEL, compress_token_limit=4000),

    # Context
    add_datetime_to_context=True,
    add_history_to_context=False,  # Disabled to prevent context overflow
    read_chat_history=False,  # Disabled to prevent context overflow
    num_history_runs=0,

    # Output
    markdown=True,
)
