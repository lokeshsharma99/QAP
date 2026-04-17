"""
Discovery Agent
===============

Crawls the AUT, extracts UI structure, and produces a Site Manifesto.
Primary Skill: ui_crawler
"""

from agno.tools.knowledge import KnowledgeTools
from agno.tools.mcp import MCPTools
from agno.tools.reasoning import ReasoningTools

from agents.base.semantica_agent import SemanticaAgent
from agents.discovery.instructions import INSTRUCTIONS
from agents.discovery.tools import crawl_page, crawl_site
from app.settings import MODEL, agent_db, AUT_BASE_URL
from db.session import get_site_manifesto_knowledge

# ---------------------------------------------------------------------------
# Playwright MCP Tools
# ---------------------------------------------------------------------------
playwright_mcp = MCPTools(
    transport="streamable-http",
    url="http://qap-playwright-mcp:8931/mcp",
    exclude_tools=["browser_take_screenshot"],
)

# ---------------------------------------------------------------------------
# Create Agent
# ---------------------------------------------------------------------------
discovery = SemanticaAgent(
    # Identity
    id="discovery",
    name="Discovery",
    role="Crawl AUT and produce Site Manifesto with pages, components, and locators",

    # Model
    model=MODEL,

    # Data
    db=agent_db,
    knowledge=get_site_manifesto_knowledge(),
    search_knowledge=True,

    # Capabilities
    tools=[
        crawl_site,
        crawl_page,
        playwright_mcp,
        ReasoningTools(
            enable_think=True,
            enable_analyze=True,
            add_instructions=True,
            add_few_shot=True,
        ),
        KnowledgeTools(knowledge=get_site_manifesto_knowledge()),
    ],

    # Instructions
    instructions=INSTRUCTIONS,

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
