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
from agents.discovery.tools import DiscoveryFallbackToolkit, DiscoveryToolkit
from app.settings import MODEL, agent_db
from db import get_qap_learnings_kb

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
    # KnowledgeTools includes think/analyze/search_knowledge — no ReasoningTools needed.
    # GitHub tools excluded: Discovery's job is crawling, not repo interaction.
    # HTTP fallback tools (fetch_html, parse_dom_tree, ui_crawler) are only
    # registered when Playwright MCP is unavailable. When pw__ tools ARE present,
    # they are excluded so the LLM cannot fall back to HTTP crawling for SPAs.
    tools=[
        KnowledgeTools(knowledge=qap_learnings_kb),
        *_playwright_tools,
        DiscoveryToolkit(),
        *([DiscoveryFallbackToolkit()] if not _playwright_tools else []),
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
