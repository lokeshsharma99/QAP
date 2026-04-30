"""
Discovery Agent
===============

Primary skill: ui_crawler
Role: Launch browser, authenticate with AUT, explore pages, generate Site Manifesto.
"""

from agno.agent import Agent
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.knowledge import KnowledgeTools
from agno.tools.reasoning import ReasoningTools

from agents.discovery.instructions import INSTRUCTIONS
from agents.discovery.tools import DiscoveryToolkit
from app.settings import MODEL, agent_db
from db import get_qap_learnings_kb, get_site_manifesto_kb

# ---------------------------------------------------------------------------
# GitHub MCP Tools (optional — requires GITHUB_TOKEN in .env)
# Discovery reads Wiki pages (Domain Knowledge, Wireframes) for AUT context
# before crawling so it knows what pages and flows to prioritise.
# ---------------------------------------------------------------------------
from app.github_mcp import get_github_mcp_for_discovery
_github_tools = get_github_mcp_for_discovery()

# ---------------------------------------------------------------------------
# Playwright MCP Tools (optional — uses PLAYWRIGHT_MCP_URL or npx headless)
# Discovery uses these to crawl the AUT in a real browser, capture
# accessibility snapshots of each page/component, and build the Site Manifesto.
# ---------------------------------------------------------------------------
from app.playwright_mcp import get_playwright_mcp_for_discovery
_playwright_tools = get_playwright_mcp_for_discovery()

# ---------------------------------------------------------------------------
# Knowledge Bases
# Primary: qap_learnings (shared collective intelligence)
# Domain:  site_manifesto — Discovery is the WRITER of this KB
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()
site_manifesto_kb = get_site_manifesto_kb()

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
    knowledge=qap_learnings_kb,
    search_knowledge=True,
    # Capabilities
    tools=[
        ReasoningTools(add_instructions=True),
        KnowledgeTools(knowledge=qap_learnings_kb),
        KnowledgeTools(knowledge=site_manifesto_kb),
        *_github_tools,
        *_playwright_tools,
        DiscoveryToolkit(),
    ],
    # Instructions
    instructions=INSTRUCTIONS,
    # Guardrails (pre-hooks for input validation)
    pre_hooks=[
        pii_detection_guardrail,
        prompt_injection_guardrail,
    ],
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
    update_memory_on_run=True,
    enable_session_summaries=False,  # Disabled — model returns empty JSON; crawl state tracked via session_state
    tool_call_limit=100,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    markdown=True,
)
