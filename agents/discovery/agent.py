"""
Discovery Agent
===============

Primary skill: ui_crawler
Role: Launch browser, authenticate with AUT, explore pages, generate Site Manifesto.
"""

from agno.agent import Agent
from app.guardrails import pii_detection_guardrail, prompt_injection_guardrail
from agno.tools.knowledge import KnowledgeTools

from agents.discovery.instructions import INSTRUCTIONS
from agents.discovery.tools import DiscoveryHTTPToolkit, DiscoveryToolkit
from app.settings import MODEL, agent_db
from contracts.site_manifesto import SiteManifesto
from db import get_qap_learnings_kb, get_culture_manager

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
# Note: site_manifesto KB is WRITTEN by Discovery via save_learning — not read.
# ---------------------------------------------------------------------------
qap_learnings_kb = get_qap_learnings_kb()

# ---------------------------------------------------------------------------
# Culture Manager
# ---------------------------------------------------------------------------
culture_manager = get_culture_manager()

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
    # Dual strategy — both toolkits are ALWAYS registered:
    #   1. DiscoveryHTTPToolkit (fetch_html, parse_dom_tree, ui_crawler):
    #      Static DOM crawl — cheaply maps link graph, form fields, page structure.
    #      Use FIRST on each URL for a fast structural overview.
    #   2. pw__* Playwright MCP tools (registered when playwright-mcp is reachable):
    #      Live browser rendering — captures the real Accessibility Tree for SPAs.
    #      Use AFTER HTTP crawl to capture what JS actually renders.
    #   3. DiscoveryToolkit (save_learning): always registered for KB persistence.
    tools=[
        KnowledgeTools(knowledge=qap_learnings_kb),
        DiscoveryHTTPToolkit(),
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
    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=5,
    # Output
    output_schema=SiteManifesto,
    markdown=True,
    followups=True,
    num_followups=3,
)
