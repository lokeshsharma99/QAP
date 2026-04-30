"""
Curator Agent
=============

Agent for regression suite curation and maintenance.
"""

import logging
from pathlib import Path

from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.file import FileTools
from agno.tools.reasoning import ReasoningTools
from agno.tools.user_feedback import UserFeedbackTools

from agents.base.semantica_agent import SemanticaAgent
from agents.curator.instructions import INSTRUCTIONS
from agents.curator.tools import (
    approve_deletion,
    DeletionToolkit,
    generate_maintenance_report,
    log_deletion_to_audit,
    reject_deletion,
    request_batch_deletion_approval,
    request_deletion_approval,
)
from app.settings import MODEL, agent_db
from db.session import get_automation_kb

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------
try:
    automation_knowledge = get_automation_kb()
except Exception:
    automation_knowledge = None

if automation_knowledge is not None:
    logger.info("Curator: Automation knowledge base loaded")
else:
    logger.warning("Curator: Automation knowledge base is None - codebase context unavailable")

# ---------------------------------------------------------------------------
# Build Tools List
# ---------------------------------------------------------------------------
# KnowledgeTools(automation_knowledge) dropped: redundant with native search_knowledge=True.
# ReasoningTools provides think/analyze. Native KB search covers automation_knowledge.
tools = [
    ReasoningTools(
        enable_think=True,
        enable_analyze=True,
        add_instructions=True,
        add_few_shot=True,
    ),
    UserFeedbackTools(),
    FileTools(Path("automation")),
    request_deletion_approval,
    request_batch_deletion_approval,
    approve_deletion,
    reject_deletion,
    DeletionToolkit(),
    log_deletion_to_audit,
    generate_maintenance_report,
]

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
curator = SemanticaAgent(
    id="curator",
    name="Curator",
    role="Maintains regression suite by detecting obsolete tests and recommending deletions with HITL approval",
    model=MODEL,
    db=agent_db,
    knowledge=automation_knowledge if automation_knowledge else None,
    search_knowledge=automation_knowledge is not None,
    tools=tools,
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        pii_detection_guardrail,
        prompt_injection_guardrail,
    ],
    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
    followups=True,
    num_followups=3,
)

logger.info("Curator agent created successfully")
