"""
Discovery Agent Tools
======================

Custom web crawling tools for the Discovery Agent (ui_crawler skill).

Primary strategy: Crawl4AI (AsyncWebCrawler) — multi-level BFS deep crawl with
  Playwright-rendered pages, clean LLM-ready fit_markdown (PruningContentFilter),
  internal link graph, and per-page metadata (depth, score).

Secondary: `fetch_page` — single-page render via plain arun() (no deep crawl overhead).

KB persistence: `DiscoveryToolkit.save_learning` — unchanged.
"""

import asyncio
import hashlib
import json
import re
from datetime import datetime
from urllib.parse import urlparse

from agno.run import RunContext
from agno.tools import Toolkit, tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Small DOM / text helpers
# ---------------------------------------------------------------------------
def _extract_title_from_html(html: str) -> str:
    """Extract the <title> tag content from an HTML string."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else "Untitled"


def _detect_auth_gate_md(text: str) -> bool:
    """Heuristically detect if a page is behind authentication from markdown or HTML text."""
    auth_indicators = ["login", "sign in", "sign-in", "signin", "unauthorized", "401", "403"]
    text_lower = (text or "").lower()
    return any(indicator in text_lower[:2000] for indicator in auth_indicators)


def _hash_content(text: str) -> str:
    """Generate a short SHA-256 hash of text content for change detection."""
    return hashlib.sha256((text or "").encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Crawl4AI async helper
# ---------------------------------------------------------------------------
def _run_async(coro):
    """Run an async coroutine from sync context (tools are called synchronously by Agno)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


def _extract_markdown(result) -> str:
    """Extract the best available markdown from a CrawlResult.

    Prefers fit_markdown (pruned) > raw_markdown > str fallback.
    """
    md = result.markdown
    if md is None:
        return ""
    if hasattr(md, "fit_markdown") and md.fit_markdown:
        return md.fit_markdown
    if hasattr(md, "raw_markdown") and md.raw_markdown:
        return md.raw_markdown
    if isinstance(md, str):
        return md
    return ""


async def _crawl4ai_deep(
    base_url: str,
    max_depth: int = 2,
    max_pages: int = 50,
) -> list[dict]:
    """
    Run a Crawl4AI BFS deep crawl and return a list of page dicts:
        {url, title, status_code, depth, score, markdown,
         links_internal, links_external, error}

    Uses fit_markdown (PruningContentFilter) to strip nav/footer boilerplate —
    ~80% fewer tokens while preserving all actionable content.
    Playwright-based rendering is handled internally by Crawl4AI.

    BrowserConfig optimisations for text-only content discovery:
    - light_mode: disables background GPU/rendering features
    - avoid_ads: blocks ad + tracker domains at the browser level
    - avoid_css: skips CSS files (we only need text + links)
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
        from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
        from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        from crawl4ai.content_filter_strategy import PruningContentFilter
    except ImportError:
        return [{"url": base_url, "error": "crawl4ai not installed. Run: pip install crawl4ai"}]

    pages: list[dict] = []

    browser_config = BrowserConfig(
        headless=True,
        user_agent=_USER_AGENT,
        light_mode=True,       # disable background rendering features
        avoid_ads=True,        # block ad/tracker domains
        avoid_css=True,        # skip CSS files — text/links only
        verbose=False,
    )

    config = CrawlerRunConfig(
        deep_crawl_strategy=BFSDeepCrawlStrategy(
            max_depth=max_depth,
            include_external=False,
            max_pages=max_pages,
        ),
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.4),
            options={"citations": False},
        ),
        # Content quality filters — reduce boilerplate noise in markdown
        word_count_threshold=10,
        excluded_tags=["nav", "header", "footer", "script", "style"],
        exclude_social_media_links=True,
        # Security: keep internal links HTTPS even if server redirects to HTTP
        preserve_https_for_internal_links=True,
        # Performance: don't wait for full network idle
        wait_until="domcontentloaded",
        stream=True,
        verbose=False,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        async for result in await crawler.arun(base_url, config=config):
            page: dict = {"url": result.url}
            if not result.success:
                page["error"] = result.error_message or "crawl failed"
                pages.append(page)
                continue

            page["status_code"] = result.status_code
            page["title"] = _extract_title_from_html(result.html or "")
            # Depth and relevance score from BFS metadata
            page["depth"] = result.metadata.get("depth", 0) if result.metadata else 0
            page["score"] = result.metadata.get("score") if result.metadata else None
            page["markdown"] = _extract_markdown(result)
            page["links_internal"] = [
                lnk.get("href", "") for lnk in result.links.get("internal", [])
            ]
            page["links_external"] = [
                lnk.get("href", "") for lnk in result.links.get("external", [])
            ]
            pages.append(page)

    return pages


async def _crawl4ai_single(url: str) -> dict:
    """
    Fetch a single page with Crawl4AI (no deep crawl strategy overhead) and
    return a page dict: {url, title, status_code, markdown, links_internal, error}

    Used by `fetch_page` — cleaner and faster than using BFSDeepCrawlStrategy
    with max_depth=0 for single-page retrieval.
    """
    try:
        from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig
        from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
        from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
        from crawl4ai.content_filter_strategy import PruningContentFilter
    except ImportError:
        return {"url": url, "error": "crawl4ai not installed. Run: pip install crawl4ai"}

    browser_config = BrowserConfig(
        headless=True,
        user_agent=_USER_AGENT,
        light_mode=True,
        avoid_ads=True,
        avoid_css=True,
        verbose=False,
    )

    config = CrawlerRunConfig(
        scraping_strategy=LXMLWebScrapingStrategy(),
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=PruningContentFilter(threshold=0.4),
            options={"citations": False},
        ),
        word_count_threshold=10,
        excluded_tags=["nav", "header", "footer", "script", "style"],
        preserve_https_for_internal_links=True,
        wait_until="domcontentloaded",
        verbose=False,
    )

    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url, config=config)

    if not result.success:
        return {"url": url, "error": result.error_message or "crawl failed"}

    return {
        "url": result.url,
        "title": _extract_title_from_html(result.html or ""),
        "status_code": result.status_code,
        "markdown": _extract_markdown(result),
        "links_internal": [
            lnk.get("href", "") for lnk in result.links.get("internal", [])
        ],
    }


# ---------------------------------------------------------------------------
# Crawl4AI Toolkit  (replaces the old DiscoveryHTTPToolkit)
# ---------------------------------------------------------------------------

class Crawl4AIToolkit(Toolkit):
    """
    Toolkit powered by Crawl4AI.

    Tools exposed to the agent:
        ui_crawler      — primary skill: multi-level BFS crawl → Site Manifesto skeleton
        fetch_page      — single-page crawl → markdown + links (replaces fetch_html + parse_dom_tree)
    """

    def __init__(self):
        super().__init__(name="crawl4ai_toolkit")
        self.register(self.ui_crawler)
        self.register(self.fetch_page)

    def ui_crawler(
        self,
        aut_base_url: str,
        max_depth: int = 2,
        max_pages: int = 50,
    ) -> str:
        """Crawl the Application Under Test with Crawl4AI BFS deep crawl and return
        a Site Manifesto skeleton as JSON.

        Uses Playwright-rendered pages internally, so JavaScript-heavy SPAs are handled
        correctly. Each page's fit_markdown field contains clean, LLM-ready content with
        boilerplate stripped. After receiving this skeleton the agent should supplement
        with pw__browser_snapshot calls to capture the accessibility tree for individual
        pages.

        Args:
            aut_base_url: Base URL of the AUT (e.g. "https://demo.example.com").
            max_depth:    BFS levels beyond the start page (default 2 = home + 2 hops).
            max_pages:    Hard cap on total pages crawled (default 50).

        Returns:
            JSON string with manifesto_id, aut_base_url, pages list, and crawl summary.
        """
        crawl_start = datetime.now()
        pages_raw = _run_async(_crawl4ai_deep(aut_base_url, max_depth, max_pages))

        parsed_base = urlparse(aut_base_url.rstrip("/"))

        pages_out = []
        for p in pages_raw:
            pages_out.append({
                "url": p.get("url"),
                "title": p.get("title", "Untitled"),
                "status_code": p.get("status_code"),
                "is_auth_gated": _detect_auth_gate_md(p.get("markdown", "")),
                "accessibility_tree_hash": _hash_content(p.get("markdown", "")),
                "markdown_preview": (p.get("markdown", "") or "")[:500],
                "links_internal": p.get("links_internal", []),
                "error": p.get("error"),
                "components": [],  # populated by Playwright MCP snapshot
            })

        successful = [p for p in pages_out if not p.get("error")]
        crawl_duration = (datetime.now() - crawl_start).total_seconds()

        result = {
            "manifesto_id": f"manifesto-{crawl_start.strftime('%Y%m%d%H%M%S')}",
            "aut_base_url": aut_base_url,
            "aut_name": parsed_base.netloc,
            "pages": pages_out,
            "crawled_at": crawl_start.isoformat(),
            "crawl_duration_seconds": round(crawl_duration, 2),
            "total_pages_crawled": len(successful),
            "total_pages_failed": len(pages_raw) - len(successful),
            "auth_handshake_success": False,
            "crawler": "crawl4ai-bfs",
            "notes": (
                f"Crawl4AI BFS deep crawl: {len(successful)} pages. "
                "Components[] are empty — use pw__browser_snapshot per page to fill them. "
                "markdown_preview contains pruned LLM-ready content."
            ),
        }
        return json.dumps(result, indent=2)

    def fetch_page(self, url: str) -> str:
        """Fetch a single page with Crawl4AI and return its full markdown + internal links.

        Faster than ui_crawler for individual pages — uses a plain arun() call
        without BFS deep crawl strategy overhead. Use this when you need the full
        fit_markdown for a specific page that was discovered by ui_crawler.

        Args:
            url: Full URL to fetch.

        Returns:
            JSON with url, title, markdown (fit), links_internal, status_code.
        """
        p = _run_async(_crawl4ai_single(url))
        return json.dumps({
            "url": p.get("url", url),
            "title": p.get("title", "Untitled"),
            "status_code": p.get("status_code"),
            "markdown": p.get("markdown", ""),
            "links_internal": p.get("links_internal", []),
            "error": p.get("error"),
        }, indent=2)


# ---------------------------------------------------------------------------
# save_learning — Tool (unchanged)
# ---------------------------------------------------------------------------
@tool(
    name="save_learning",
    description="Save a reusable crawling insight to the knowledge base.",
)
def save_learning(run_context: RunContext, title: str, insight: str) -> str:
    """Save a reusable crawling insight to the knowledge base.

    Args:
        run_context: Run context providing access to the agent's knowledge base.
        title: Descriptive title for the learning (used for retrieval).
        insight: The detailed insight or pattern to save.

    Returns:
        Confirmation message.
    """
    if run_context.knowledge:
        run_context.knowledge.insert(name=title, text_content=insight)
        return f"Saved learning: '{title}'"
    return "Knowledge base not available in run context"


# ---------------------------------------------------------------------------
# DiscoveryToolkit — wraps save_learning for Agno tool registration
# ---------------------------------------------------------------------------
class DiscoveryToolkit(Toolkit):
    """Toolkit containing knowledge-base tools for the Discovery Agent."""

    def __init__(self):
        super().__init__(name="discovery_toolkit")
        self.register(save_learning)
