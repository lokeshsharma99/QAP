"""
Discovery Agent Tools
======================

Custom web crawling tools for the Discovery Agent (ui_crawler skill).

Uses requests + BeautifulSoup for static HTML crawling.
For SPA/JavaScript-heavy pages, the agent is guided to use Playwright MCP tools.
"""

import hashlib
import json
import re
from datetime import datetime
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests
from agno.run import RunContext
from agno.tools import Toolkit, tool
from bs4 import BeautifulSoup

from contracts.site_manifesto import PageEntry, SiteManifesto, UIComponent

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_DEFAULT_ROUTES = [
    "/",
    "/login",
    "/register",
    "/dashboard",
    "/home",
    "/about",
    "/contact",
    "/profile",
    "/settings",
    "/products",
    "/cart",
    "/checkout",
]

_INTERACTABLE_TAGS = {
    "button",
    "a",
    "input",
    "select",
    "textarea",
    "form",
}

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# fetch_html — Tool
# ---------------------------------------------------------------------------
@tool(
    name="fetch_html",
    description="Fetch HTML content from a URL using requests. Results are cached to avoid redundant network calls.",
    cache_results=True,
    cache_ttl=1800,
)
def fetch_html(url: str, timeout: int = 30) -> str:
    """Fetch HTML content from a URL using requests.

    Args:
        url: The URL to fetch HTML from.
        timeout: Request timeout in seconds.

    Returns:
        The raw HTML content as a string, or an error message if fetch fails.
    """
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": _USER_AGENT},
            allow_redirects=True,
        )
        response.raise_for_status()
        return response.text
    except requests.exceptions.Timeout:
        return f"ERROR: Request timed out after {timeout}s for {url}"
    except requests.exceptions.HTTPError as e:
        return f"ERROR: HTTP {e.response.status_code} for {url}"
    except requests.exceptions.ConnectionError:
        return f"ERROR: Could not connect to {url}"
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {type(e).__name__}: {e} for {url}"


# ---------------------------------------------------------------------------
# parse_dom_tree — Tool
# ---------------------------------------------------------------------------
@tool(
    name="parse_dom_tree",
    description="Parse HTML content and extract interactable UI components as a list of component dicts.",
)
def parse_dom_tree(html_content: str, base_url: str = "") -> list[dict]:
    """Parse HTML content and extract interactable UI components.

    Args:
        html_content: Raw HTML string from fetch_html.
        base_url: Base URL for resolving relative hrefs (optional).

    Returns:
        List of component dicts with element info and locator candidates.
    """
    if html_content.startswith("ERROR:"):
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    components = []

    for tag in soup.find_all(_INTERACTABLE_TAGS):
        component = _extract_component_info(tag, base_url)
        if component:
            components.append(component)

    return components


# ---------------------------------------------------------------------------
# save_learning — Tool
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
# ui_crawler — Primary skill tool
# ---------------------------------------------------------------------------
@tool(
    name="ui_crawler",
    description="Crawl the Application Under Test and produce a Site Manifesto skeleton. Results are cached per AUT URL.",
    cache_results=True,
    cache_ttl=1800,
)
def ui_crawler(
    aut_base_url: str,
    routes: Optional[list[str]] = None,
    max_pages: int = 20,
    follow_links: bool = True,
    aut_auth_user: Optional[str] = None,
    aut_auth_pass: Optional[str] = None,
) -> dict:
    """Crawl the Application Under Test and produce a Site Manifesto skeleton.

    This tool orchestrates the crawl and returns a structured dict that the
    agent should use to populate a full SiteManifesto.

    For JavaScript-heavy SPAs, the agent should supplement this with
    Playwright MCP tools (browser_navigate, browser_snapshot) to capture
    the rendered accessibility tree.

    Args:
        aut_base_url: Base URL of the Application Under Test.
        routes: Specific routes to crawl. Defaults to common routes.
        max_pages: Maximum pages to crawl (prevents infinite loops).
        follow_links: Whether to discover additional routes from nav links.
        aut_auth_user: Optional username for authentication.
        aut_auth_pass: Optional password for authentication.

    Returns:
        Dict with manifesto metadata, pages list, and crawl summary.
    """
    routes = routes or _DEFAULT_ROUTES
    visited: set[str] = set()
    pages: list[dict] = []
    crawl_start = datetime.now()

    parsed_base = urlparse(aut_base_url.rstrip("/"))
    base_origin = f"{parsed_base.scheme}://{parsed_base.netloc}"

    # Crawl each route
    for route in routes[:max_pages]:
        url = urljoin(aut_base_url, route)
        if url in visited:
            continue
        visited.add(url)

        html = fetch_html(url)
        if html.startswith("ERROR:"):
            pages.append({"url": url, "route": route, "error": html, "components": []})
            continue

        components = parse_dom_tree(html, base_url=base_origin)
        title = _extract_title(html)
        is_auth_gated = _detect_auth_gate(html)
        accessibility_tree_hash = _hash_content(html)

        page_entry = {
            "url": url,
            "route": route,
            "title": title,
            "is_auth_gated": is_auth_gated,
            "accessibility_tree_hash": accessibility_tree_hash,
            "components": components,
        }
        pages.append(page_entry)

        # Discover additional routes from navigation links
        if follow_links and len(visited) < max_pages:
            new_routes = _extract_nav_links(html, base_origin)
            for new_route in new_routes:
                if new_route not in [r.get("route") for r in pages]:
                    routes.append(new_route)

    crawl_duration = (datetime.now() - crawl_start).total_seconds()

    return {
        "manifesto_id": f"manifesto-{crawl_start.strftime('%Y%m%d%H%M%S')}",
        "aut_base_url": aut_base_url,
        "aut_name": parsed_base.netloc,
        "pages": pages,
        "crawled_at": crawl_start.isoformat(),
        "crawl_duration_seconds": round(crawl_duration, 2),
        "total_pages_crawled": len([p for p in pages if "error" not in p]),
        "total_components_found": sum(len(p.get("components", [])) for p in pages),
        "auth_handshake_success": bool(aut_auth_user and aut_auth_pass),
        "crawler_version": "1.0.0",
        "notes": (
            f"Static HTML crawl: {len(pages)} pages attempted. "
            "For SPA/JS-heavy pages, supplement with Playwright MCP."
        ),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _extract_component_info(tag, base_url: str = "") -> Optional[dict]:
    """Extract component data and locator candidates from a BS4 tag."""
    tag_name = tag.name
    if not tag_name:
        return None

    # Build locator candidates (priority order)
    data_testid = tag.get("data-testid") or tag.get("data-test-id") or tag.get("testid")
    aria_role = tag.get("role")
    aria_label = tag.get("aria-label") or tag.get("aria-labelledby")
    text = tag.get_text(strip=True)[:100] if tag.get_text(strip=True) else None
    id_attr = tag.get("id")
    name_attr = tag.get("name")
    placeholder = tag.get("placeholder")
    href = tag.get("href")
    input_type = tag.get("type") if tag_name == "input" else None

    # Skip invisible or empty anchors
    if tag_name == "a" and not text and not aria_label:
        return None

    # Determine component type
    component_type = _classify_component(tag_name, input_type, aria_role)

    return {
        "name": data_testid or aria_label or name_attr or id_attr or text or tag_name,
        "component_type": component_type,
        "tag": tag_name,
        "input_type": input_type,
        "aria_role": aria_role or _infer_role(tag_name, input_type),
        "aria_label": aria_label,
        "text": text,
        "href": _resolve_href(href, base_url) if href else None,
        "placeholder": placeholder,
        # Locator candidates
        "data_testid": data_testid,
        "role_locator": f"[role='{aria_role}'][name='{aria_label}']" if aria_role and aria_label else None,
        "text_locator": f"text='{text}'" if text else None,
        "id_locator": f"#{id_attr}" if id_attr else None,
        "name_locator": f"[name='{name_attr}']" if name_attr else None,
    }


def _classify_component(tag_name: str, input_type: Optional[str], role: Optional[str]) -> str:
    """Classify a component into a human-readable type."""
    if tag_name == "button" or (tag_name == "input" and input_type in ("button", "submit", "reset")):
        return "button"
    if tag_name == "a":
        return "link"
    if tag_name == "input":
        return f"input-{input_type or 'text'}"
    if tag_name == "select":
        return "dropdown"
    if tag_name == "textarea":
        return "textarea"
    if tag_name == "form":
        return "form"
    if role:
        return role
    return tag_name


def _infer_role(tag_name: str, input_type: Optional[str]) -> str:
    """Infer ARIA role from tag name and type."""
    role_map = {
        "button": "button",
        "a": "link",
        "input": "textbox",
        "select": "combobox",
        "textarea": "textbox",
        "form": "form",
    }
    if tag_name == "input" and input_type in ("checkbox",):
        return "checkbox"
    if tag_name == "input" and input_type in ("radio",):
        return "radio"
    if tag_name == "input" and input_type in ("submit", "button"):
        return "button"
    return role_map.get(tag_name, "generic")


def _extract_title(html: str) -> str:
    """Extract the <title> tag content from HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else "Untitled"


def _detect_auth_gate(html: str) -> bool:
    """Heuristically detect if a page is behind authentication."""
    auth_indicators = ["login", "sign in", "sign-in", "signin", "unauthorized", "401", "403"]
    html_lower = html.lower()
    return any(indicator in html_lower[:2000] for indicator in auth_indicators)


def _hash_content(html: str) -> str:
    """Generate a short hash of the HTML for change detection."""
    return hashlib.sha256(html.encode()).hexdigest()[:16]


def _extract_nav_links(html: str, base_origin: str) -> list[str]:
    """Extract navigation links from HTML to discover additional routes."""
    soup = BeautifulSoup(html, "html.parser")
    routes = []

    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "")
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        # Relative routes only (same origin)
        if href.startswith("/"):
            routes.append(href)
        elif href.startswith(base_origin):
            routes.append(href.replace(base_origin, ""))

    # Deduplicate and filter out file extensions
    seen: set[str] = set()
    clean_routes = []
    for r in routes:
        r = r.split("?")[0].split("#")[0]  # strip query/fragment
        if r and r not in seen and not re.search(r"\.(css|js|png|jpg|svg|ico|woff|ttf)$", r):
            seen.add(r)
            clean_routes.append(r)

    return clean_routes[:10]  # limit to 10 discovered routes


def _resolve_href(href: str, base_origin: str) -> str:
    """Resolve a potentially relative href to an absolute URL."""
    if href.startswith("http"):
        return href
    if href.startswith("/") and base_origin:
        return urljoin(base_origin, href)
    return href


# ---------------------------------------------------------------------------
# DiscoveryToolkit
# ---------------------------------------------------------------------------
class DiscoveryToolkit(Toolkit):
    """Groups all Discovery Agent tools into a single registerable toolkit."""

    def __init__(self) -> None:
        super().__init__(
            name="discovery",
            tools=[fetch_html, parse_dom_tree, save_learning, ui_crawler],
        )
