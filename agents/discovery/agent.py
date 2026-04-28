"""
Discovery Agent
===============

Primary skill: ui_crawler
Role: Launch browser, authenticate with AUT, explore pages, generate Site Manifesto.
"""

from agno.agent import Agent
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.discovery.instructions import INSTRUCTIONS
from agents.discovery.tools import fetch_html, parse_dom_tree, save_learning, ui_crawler
from app.settings import MODEL, agent_db
from db import create_knowledge

# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------
discovery_knowledge = create_knowledge(
    name="Discovery Knowledge",
    table_name="discovery_knowledge",
)

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
discovery = Agent(
    # Identity
    id="discovery",
    name="Discovery",
    role="Crawl AUT, map UI components, generate Site Manifesto",
    # Model
    model=MODEL,
    # Data
    db=agent_db,
    knowledge=discovery_knowledge,
    search_knowledge=True,
    # Capabilities
    tools=[
        ReasoningTools(add_instructions=True),
        KnowledgeTools(knowledge=discovery_knowledge),
        fetch_html,
        parse_dom_tree,
        save_learning,
        ui_crawler,
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Feature-specific
    session_state={
        "crawled_pages": [],
        "discovered_components": [],
        "site_manifesto": None,
        "current_url": None,
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
