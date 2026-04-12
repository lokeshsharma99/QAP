"""
Discovery Agent Tools
=====================

The ui_crawler tool navigates the AUT, extracts page structure,
and builds a Site Manifesto with interactive elements and locators.

Uses curl_cffi for static sites. For SPAs, the agent should use Playwright MCP tools directly.
"""

import hashlib
import json
import time
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from agno.tools import tool
from bs4 import BeautifulSoup, Tag
from curl_cffi import requests as cf_requests

from contracts.site_manifesto import LocatorStrategy, PageEntry, SiteManifesto, UIComponent

# ---------------------------------------------------------------------------
# High-risk keywords (flagged for manual review)
# ---------------------------------------------------------------------------
HIGH_RISK_KEYWORDS = {"delete", "remove", "purge", "destroy", "reset", "cancel order", "deactivate"}


def _fetch_page(url: str, timeout: int = 20) -> cf_requests.Response | None:
    """Fetch a page using curl_cffi with Chrome TLS impersonation to bypass Cloudflare."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    try:
        # Try with Chrome120 impersonation first
        response = cf_requests.get(
            url,
            impersonate="chrome120",
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        )
        if response.status_code == 200:
            return response
        
        # If that fails, try with chrome
        response = cf_requests.get(
            url,
            impersonate="chrome",
            headers=headers,
            timeout=timeout,
            allow_redirects=True
        )
        if response.status_code == 200:
            return response
            
        return None
    except Exception:
        return None


def _determine_locator(element: Tag) -> tuple[LocatorStrategy, str]:
    """Determine the best locator strategy for an element."""
    # Priority: data-testid > role+name > aria-label > id > name > text
    if element.get("data-testid"):
        return LocatorStrategy.DATA_TESTID, element["data-testid"]
    if element.get("role") and element.get("aria-label"):
        return LocatorStrategy.ROLE, f'{element["role"]}:{element["aria-label"]}'
    if element.get("aria-label"):
        return LocatorStrategy.LABEL, element["aria-label"]
    if element.get("id"):
        return LocatorStrategy.NAME, element["id"]
    if element.get("name"):
        return LocatorStrategy.NAME, element["name"]
    if element.get("placeholder"):
        return LocatorStrategy.PLACEHOLDER, element["placeholder"]

    text = element.get_text(strip=True)[:80]
    if text:
        return LocatorStrategy.TEXT, text

    return LocatorStrategy.TEXT, element.name


def _is_high_risk(text: str) -> bool:
    """Check if element text suggests a dangerous action."""
    lower = text.lower()
    return any(kw in lower for kw in HIGH_RISK_KEYWORDS)


def _extract_components(soup: BeautifulSoup) -> list[UIComponent]:
    """Extract all interactive UI components from a page."""
    components: list[UIComponent] = []

    # Buttons
    for btn in soup.find_all(["button", "input"], attrs={"type": lambda t: t in ("submit", "button", "reset", None)}):
        if btn.name == "input" and btn.get("type") not in ("submit", "button", "reset"):
            continue
        text = btn.get_text(strip=True) or btn.get("value", "")
        strategy, value = _determine_locator(btn)
        components.append(
            UIComponent(
                tag=btn.name,
                text=text,
                component_type="action",
                locator_strategy=strategy,
                locator_value=value,
                aria_role=btn.get("role", "button"),
                aria_label=btn.get("aria-label", ""),
                element_id=btn.get("id", ""),
                element_name=btn.get("name", ""),
                input_type=btn.get("type", ""),
                is_high_risk=_is_high_risk(text),
                data_testid=btn.get("data-testid", ""),
            )
        )

    # Text inputs, selects, textareas
    for inp in soup.find_all(["input", "select", "textarea"]):
        inp_type = inp.get("type", "text")
        if inp_type in ("hidden", "submit", "button", "reset"):
            continue
        text = inp.get("placeholder", "") or inp.get("aria-label", "") or inp.get("name", "")
        strategy, value = _determine_locator(inp)
        components.append(
            UIComponent(
                tag=inp.name,
                text=text,
                component_type="form-field",
                locator_strategy=strategy,
                locator_value=value,
                aria_role=inp.get("role", ""),
                aria_label=inp.get("aria-label", ""),
                element_id=inp.get("id", ""),
                element_name=inp.get("name", ""),
                input_type=inp_type,
                data_testid=inp.get("data-testid", ""),
            )
        )

    # Links (navigation)
    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True)
        if not text or len(text) < 2:
            continue
        strategy, value = _determine_locator(link)
        components.append(
            UIComponent(
                tag="a",
                text=text[:80],
                component_type="navigation",
                locator_strategy=strategy,
                locator_value=value,
                aria_role=link.get("role", "link"),
                aria_label=link.get("aria-label", ""),
                element_id=link.get("id", ""),
                href=link.get("href", ""),
                is_high_risk=_is_high_risk(text),
                data_testid=link.get("data-testid", ""),
            )
        )

    return components


def _extract_links(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract all internal links from a page."""
    links: list[str] = []
    base_domain = urlparse(base_url).netloc

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)

        # Only internal links, no anchors, no mailto, no javascript
        if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if clean_url not in links:
                links.append(clean_url)

    return links


def _compute_tree_hash(components: list[UIComponent]) -> str:
    """Compute a hash of the page's component structure for change detection."""
    tree_str = json.dumps([c.model_dump() for c in components], sort_keys=True)
    return hashlib.sha256(tree_str.encode()).hexdigest()[:16]


def _parse_page(url: str, html: str) -> PageEntry:
    """Parse HTML into a PageEntry with components and links."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag and meta_tag.get("content"):
        meta_desc = meta_tag["content"]

    components = _extract_components(soup)
    links = _extract_links(soup, url)
    forms_count = len(soup.find_all("form"))

    return PageEntry(
        url=url,
        path=urlparse(url).path or "/",
        title=title,
        description=meta_desc,
        requires_auth=False,
        components=components,
        links=links,
        forms=forms_count,
        accessibility_tree_hash=_compute_tree_hash(components),
    )


@tool(name="crawl_page", description="Crawl a single page of the AUT and extract its structure, components, and links.")
def crawl_page(url: str) -> str:
    """Crawl a single page and extract its UI components.

    Args:
        url: The full URL of the page to crawl.

    Returns:
        JSON string with page entry data including components and links.
    """
    response = _fetch_page(url)
    if response is None:
        return json.dumps({"error": f"Failed to fetch {url} (Cloudflare or network error)"})

    page = _parse_page(url, response.text)
    return page.model_dump_json(indent=2)


@tool(
    name="crawl_site",
    description="Crawl the AUT starting from the base URL. Discovers pages, extracts UI components, and generates a Site Manifesto. For SPAs, use Playwright MCP tools directly.",
)
def crawl_site(base_url: str, max_pages: int = 10) -> str:
    """Crawl the Application Under Test and generate a Site Manifesto.

    Args:
        base_url: The base URL of the AUT (e.g., https://demo.nopcommerce.com/).
        max_pages: Maximum number of pages to crawl (default: 10).

    Returns:
        JSON string with the complete Site Manifesto.
    """
    visited: set[str] = set()
    to_visit: list[str] = [base_url.rstrip("/")]
    pages: list[PageEntry] = []
    high_risk_actions: list[str] = []
    auth_url = ""

    base_domain = urlparse(base_url).netloc

    while to_visit and len(visited) < max_pages:
        url = to_visit.pop(0)

        # Normalize URL
        parsed = urlparse(url)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")

        if clean_url in visited:
            continue

        # Skip non-page resources
        skip_extensions = (".jpg", ".jpeg", ".png", ".gif", ".css", ".js", ".ico", ".svg", ".pdf", ".xml", ".rss")
        if any(parsed.path.lower().endswith(ext) for ext in skip_extensions):
            continue

        visited.add(clean_url)

        # Fetch with Cloudflare bypass
        response = _fetch_page(clean_url)
        if response is None:
            continue

        # Small delay between page fetches (be respectful)
        time.sleep(0.5)

        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Detect Cloudflare challenge pages
        if "Just a moment" in title:
            continue

        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag and meta_tag.get("content"):
            meta_desc = meta_tag["content"]

        components = _extract_components(soup)
        links = _extract_links(soup, clean_url)
        forms_count = len(soup.find_all("form"))

        # Detect login page
        has_password = bool(soup.find("input", attrs={"type": "password"}))
        if has_password and not auth_url:
            auth_url = clean_url

        # Flag high-risk actions
        for comp in components:
            if comp.is_high_risk:
                high_risk_actions.append(f"[{clean_url}] {comp.tag}: '{comp.text}'")

        page = PageEntry(
            url=clean_url,
            path=parsed.path or "/",
            title=title,
            description=meta_desc,
            requires_auth=False,
            components=components,
            links=links,
            forms=forms_count,
            accessibility_tree_hash=_compute_tree_hash(components),
        )
        pages.append(page)

        # Queue new internal links
        for link in links:
            link_parsed = urlparse(link)
            if link_parsed.netloc == base_domain and link not in visited:
                to_visit.append(link)

    total_components = sum(len(p.components) for p in pages)

    manifesto = SiteManifesto(
        aut_base_url=base_url,
        aut_name=pages[0].title if pages else "",
        crawl_timestamp=datetime.now(timezone.utc).isoformat(),
        total_pages=len(pages),
        total_components=total_components,
        pages=pages,
        auth_required=bool(auth_url),
        auth_url=auth_url,
        high_risk_actions=high_risk_actions,
    )

    return manifesto.model_dump_json(indent=2)
