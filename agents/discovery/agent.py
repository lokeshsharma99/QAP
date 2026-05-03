"""
Discovery Agent
===============

Primary skill: ui_crawler
Role: Launch browser, authenticate with AUT, explore pages, generate Site Manifesto.
"""

from agno.agent import Agent
from agno.compression.manager import CompressionManager
from agno.learn import EntityMemoryConfig, LearningMachine, LearningMode
from agno.run import RunContext

from agents.discovery.instructions import INSTRUCTIONS, INSTRUCTIONS_HTTP_ONLY
from agents.discovery.tools import Crawl4AIToolkit, DiscoveryToolkit
from app.settings import MODEL, agent_db, FOLLOWUP_MODEL
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
# Context Compression
# ---------------------------------------------------------------------------
# Compress accumulated tool results when context exceeds 4 000 tokens.
# Older tool call results (HTML snapshots, DOM trees, Playwright outputs) are
# individually summarised by the lighter FOLLOWUP_MODEL, preserving key facts
# (URLs, locators, component names) while stripping verbose boilerplate.
# This mirrors the pattern used in detective/agent.py and ci_log_analyzer/agent.py.
_compression_manager = CompressionManager(
    model=FOLLOWUP_MODEL,       # lightweight model for compression summaries
    compress_token_limit=4000,  # trigger when accumulated tool results hit ~4 k tokens
)

# ---------------------------------------------------------------------------
# Dynamic Instructions
# ---------------------------------------------------------------------------
# Generate the system prompt at run-time so token count adapts to tool availability:
#   - Playwright MCP running → full dual-strategy instructions
#   - Playwright MCP absent  → HTTP-only instructions (saves ~700 tokens/call)
def _build_instructions(run_context: RunContext) -> str:
    return INSTRUCTIONS if _playwright_tools else INSTRUCTIONS_HTTP_ONLY

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
    #   1. Crawl4AIToolkit (ui_crawler, fetch_page):
    #      BFS deep crawl via Crawl4AI — Playwright-rendered pages, fit_markdown
    #      output, internal link graph. Replaces the old requests+BeautifulSoup
    #      DiscoveryHTTPToolkit. Use FIRST to map the full link graph.
    #   2. pw__* Playwright MCP tools (registered when playwright-mcp is reachable):
    #      Live browser rendering — captures the real Accessibility Tree for SPAs.
    #      Use AFTER ui_crawler to snapshot components per page.
    #   3. DiscoveryToolkit (save_learning): always registered for KB persistence.
    # NOTE: KnowledgeTools removed — search_knowledge=True already registers
    # search_knowledge_base natively, avoiding a duplicate tool definition.
    tools=[
        Crawl4AIToolkit(),
        *_playwright_tools,
        DiscoveryToolkit(),
    ],
    # Instructions — dynamic function: full dual-strategy when Playwright is
    # available, HTTP-only (~700 tokens smaller) when it isn't.
    # Avoids sending unused Playwright tool descriptions on every LLM call.
    instructions=_build_instructions,
    # Guardrails (pre-hooks for input validation)
    # Note: pii_detection_guardrail excluded — AUT accessibility trees contain
    # email/phone input fields and placeholder values that match PII patterns.
    # Context compression — summarise tool results when accumulated context hits
    # ~4 000 tokens (same strategy as detective/agent.py and ci_log_analyzer/agent.py).
    # Playwright snapshots and HTML DOM dumps are highly verbose; compression keeps
    # the LLM context lean across 20+ tool calls without losing key facts.
    compression_manager=_compression_manager,
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
    # EntityMemoryConfig(ALWAYS): auto-extracts AUT entities (pages, components, URL patterns,
    # selectors) from every crawl conversation and stores them as structured facts shared across
    # users/sessions. Highest-value config for Discovery — the whole job is entity extraction.
    learning=LearningMachine(
        entity_memory=EntityMemoryConfig(mode=LearningMode.ALWAYS),
    ),
    update_memory_on_run=True,
    enable_session_summaries=False,  # Disabled — model returns empty JSON; crawl state tracked via session_state
    tool_call_limit=100,
    # Culture
    culture_manager=culture_manager,
    add_culture_to_context=True,
    enable_agentic_culture=True,
    # Context — reduced history depth to limit token accumulation from prior runs.
    # Each Discovery run can include 20+ tool calls; loading 5 runs = ~100 tool call
    # results flooding the context. max_tool_calls_from_history caps this per run.
    add_datetime_to_context=True,
    add_history_to_context=True,
    read_chat_history=True,
    num_history_runs=2,               # reduced from 5: each run is very tool-call-heavy
    max_tool_calls_from_history=3,    # keep only last 3 tool call results per history run
    # Output
    markdown=True,
    followups=True,
    followup_model=FOLLOWUP_MODEL,
    num_followups=3,
)
