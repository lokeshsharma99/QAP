"""One-shot BFS crawl utility — reads AUT base URL from AUT_BASE_URL env var.

Usage:
    python -m scripts._crawl_aut                        # uses $AUT_BASE_URL
    python -m scripts._crawl_aut https://example.com    # explicit URL override
"""
import asyncio
import json
import sys
from os import getenv

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

# ---------------------------------------------------------------------------
# Configuration — never hardcode; read from env or accept a CLI argument
# ---------------------------------------------------------------------------
BASE_URL: str = sys.argv[1] if len(sys.argv) > 1 else getenv("AUT_BASE_URL", "")
MAX_PAGES: int = int(getenv("AUT_MAX_PAGES", "50"))
MAX_DEPTH: int = int(getenv("AUT_MAX_DEPTH", "2"))

if not BASE_URL:
    print(
        "ERROR: No AUT URL provided.\n"
        "  Set AUT_BASE_URL env var, or pass the URL as the first argument:\n"
        "  python -m scripts._crawl_aut https://your-app.example.com",
        file=sys.stderr,
    )
    sys.exit(1)

browser_cfg = BrowserConfig(headless=True, verbose=False, light_mode=True, avoid_ads=True, avoid_css=True)
run_cfg = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    word_count_threshold=10,
    excluded_tags=["nav", "header", "footer"],
    exclude_social_media_links=True,
    preserve_https_for_internal_links=True,
    wait_until="domcontentloaded",
    deep_crawl_strategy=BFSDeepCrawlStrategy(max_depth=MAX_DEPTH, max_pages=MAX_PAGES),
    markdown_generator=DefaultMarkdownGenerator(content_filter=PruningContentFilter()),
    stream=True,
    verbose=False,
)


async def crawl() -> list[dict]:
    pages: list[dict] = []
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        async for r in await crawler.arun(BASE_URL, config=run_cfg):
            if not r.success:
                pages.append({"url": r.url, "error": r.error_message or "failed"})
                continue
            md_obj = r.markdown
            if isinstance(md_obj, str):
                md = md_obj
            elif hasattr(md_obj, "fit_markdown") and md_obj.fit_markdown:
                md = md_obj.fit_markdown
            elif hasattr(md_obj, "raw_markdown") and md_obj.raw_markdown:
                md = md_obj.raw_markdown
            else:
                md = str(md_obj) if md_obj else ""
            int_links = [
                lnk.get("href", "") if isinstance(lnk, dict) else str(lnk)
                for lnk in (r.links or {}).get("internal", [])
            ]
            pages.append({
                "url": r.url,
                "title": (r.metadata or {}).get("title", ""),
                "markdown": md,
                "links": int_links,
            })
    return pages


if __name__ == "__main__":
    result = asyncio.run(crawl())
    print(json.dumps(result, indent=2))

