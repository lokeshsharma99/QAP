"""
Architect Agent
===============

Analyzes requirements, queries KB for impact, produces RequirementContext.
Primary Skill: semantic_search
"""

import logging
import os

from agno.agent import Agent
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.architect.instructions import INSTRUCTIONS
from agents.architect.tools import add_jira_comment, fetch_jira_ticket
from app.settings import MODEL, agent_db
from db.session import get_site_manifesto_knowledge, get_codebase_knowledge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Knowledge Bases
# ---------------------------------------------------------------------------
site_manifesto_knowledge = get_site_manifesto_knowledge()
codebase_knowledge = get_codebase_knowledge()

# Log knowledge base availability
if site_manifesto_knowledge is not None:
    logger.info("Architect: Site Manifesto knowledge base loaded")
else:
    logger.warning("Architect: Site Manifesto knowledge base is None - semantic search unavailable")

if codebase_knowledge is not None:
    logger.info("Architect: Codebase knowledge base loaded")
else:
    logger.warning("Architect: Codebase knowledge base is None - semantic search unavailable")

# ---------------------------------------------------------------------------
# Build Tools List
# ---------------------------------------------------------------------------
tools = [ReasoningTools(add_instructions=True)]

# Knowledge Tools
if site_manifesto_knowledge is not None:
    tools.append(KnowledgeTools(knowledge=site_manifesto_knowledge))
else:
    logger.warning("Architect: Skipping Site Manifesto KnowledgeTools due to None knowledge base")

if codebase_knowledge is not None:
    tools.append(KnowledgeTools(knowledge=codebase_knowledge))
else:
    logger.warning("Architect: Skipping Codebase KnowledgeTools due to None knowledge base")

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
architect = Agent(
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
