"""
Curator Agent
=============

Agent for regression suite curation and maintenance.
"""

import logging
from pathlib import Path

from agno.tools.file import FileTools
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
from agents.curator.instructions import INSTRUCTIONS
from agents.curator.tools import (
    approve_deletion,
    delete_scenario_from_feature,
    execute_test_deletion,
    generate_maintenance_report,
    log_deletion_to_audit,
    reject_deletion,
    request_batch_deletion_approval,
    request_deletion_approval,
)
from app.settings import MODEL, agent_db
from db.session import get_automation_knowledge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------
try:
    automation_knowledge = get_automation_knowledge()
except Exception:
    automation_knowledge = None

if automation_knowledge is not None:
    logger.info("Curator: Automation knowledge base loaded")
else:
    logger.warning("Curator: Automation knowledge base is None - codebase context unavailable")

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
    FileTools(Path("automation")),
]

# Add KnowledgeTools if knowledge base is available
if automation_knowledge is not None:
    tools.append(KnowledgeTools(knowledge=automation_knowledge))
else:
    logger.warning("Curator: Skipping KnowledgeTools due to None knowledge base")

# Add Curator-specific tools
tools.extend([
    request_deletion_approval,
    request_batch_deletion_approval,
    approve_deletion,
    reject_deletion,
    execute_test_deletion,
    delete_scenario_from_feature,
    log_deletion_to_audit,
    generate_maintenance_report,
])

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
    enable_agentic_memory=True,
    add_learnings_to_context=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    markdown=True,
)

logger.info("Curator agent created successfully")
