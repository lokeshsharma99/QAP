"""
Architect Agent
===============

Analyzes requirements, queries KB for impact, produces RequirementContext.
Primary Skill: semantic_search
"""

import logging
import os

from agno.guardrails import PIIDetectionGuardrail, PromptInjectionGuardrail
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.architect.instructions import INSTRUCTIONS
from agents.architect.tools import add_jira_comment, fetch_jira_ticket
from agents.base.semantica_agent import SemanticaAgent
from app.settings import MODEL, agent_db
from db.session import get_site_manifesto_knowledge, get_automation_knowledge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Knowledge Bases
# ---------------------------------------------------------------------------
site_manifesto_knowledge = get_site_manifesto_knowledge()
automation_knowledge = get_automation_knowledge()

# Log knowledge base availability
if site_manifesto_knowledge is not None:
    logger.info("Architect: Site Manifesto knowledge base loaded")
else:
    logger.warning("Architect: Site Manifesto knowledge base is None - context unavailable")

if automation_knowledge is not None:
    logger.info("Architect: Automation knowledge base loaded")
else:
    logger.warning("Architect: Automation knowledge base is None - context unavailable")

# ---------------------------------------------------------------------------
# Build Tools List
# ---------------------------------------------------------------------------
tools = [ReasoningTools(
    enable_think=True,
    enable_analyze=True,
    add_instructions=True,
    add_few_shot=True,
)]

# Knowledge Tools
if site_manifesto_knowledge is not None:
    tools.append(KnowledgeTools(knowledge=site_manifesto_knowledge))
else:
    logger.warning("Architect: Skipping Site Manifesto KnowledgeTools due to None knowledge base")

if automation_knowledge is not None:
    tools.append(KnowledgeTools(knowledge=automation_knowledge))
else:
    logger.warning("Architect: Skipping Automation KnowledgeTools due to None knowledge base")

# Jira API Tool (if configured)
if os.getenv("JIRA_URL") and os.getenv("JIRA_API_TOKEN"):
    tools.append(fetch_jira_ticket)
    tools.append(add_jira_comment)
    logger.info("Architect: Jira API tools loaded")
else:
    logger.info("Architect: Jira API tools not configured (missing JIRA_URL or JIRA_API_TOKEN)")

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
architect = SemanticaAgent(
    # Identity
    id="architect",
    name="Architect",
    role="Analyze requirements, query KB for impact, produce RequirementContext",

    # Model
    model=MODEL,

    # Data
    db=agent_db,
    knowledge=site_manifesto_knowledge if site_manifesto_knowledge else None,
    search_knowledge=site_manifesto_knowledge is not None,

    # Capabilities
    tools=tools,

    # Instructions
    instructions=INSTRUCTIONS,

    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        PIIDetectionGuardrail(),
        PromptInjectionGuardrail(),
    ],

    # Memory
    enable_agentic_memory=True,
    learning=True,
    add_learnings_to_context=True,
    update_memory_on_run=True,
    enable_session_summaries=True,

    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,

    # Output
    markdown=True,
)
