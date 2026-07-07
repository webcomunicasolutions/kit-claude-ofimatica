#!/usr/bin/env python3
"""
Documentation-specialized scraper that intelligently crawls documentation sites.

Automatically detects documentation frameworks (Docusaurus, GitBook, MkDocs, etc.),
extracts sidebar navigation for ordered crawling, and optionally consolidates all
pages into a single FULL_DOCS.md file.

Usage:
    python3 scrape_docs.py "https://docs.example.com" -o ./output
    python3 scrape_docs.py "https://docs.example.com" -c -m 100
    python3 scrape_docs.py "https://docs.example.com" -j --consolidate
"""

import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

# Ensure the script's own directory is on sys.path so sibling imports work
# regardless of the caller's working directory.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from utils import (
    ScrapingError,
    check_robots_txt,
    create_session,
    detect_dynamic_content,
    fetch_page,
    is_internal_link,
    load_index,
    normalize_url,
    render_with_playwright,
    sanitize_filename,
    save_index,
    setup_output_dir,
)
from html_to_markdown import convert_html_to_markdown

logger = logging.getLogger("scrape_docs")

# ---------------------------------------------------------------------------
# Framework selectors (fallback when references/selectors-guide.md unavailable)
# ---------------------------------------------------------------------------

FRAMEWORK_SELECTORS: Dict[str, Dict[str, object]] = {
    "docusaurus": {
        "content": "article.markdown, .theme-doc-markdown",
        "sidebar": ".theme-doc-sidebar-container nav, .menu__list",
        "sidebar_links": ".menu__link",
        "remove": [
            ".theme-doc-footer", ".pagination-nav", ".theme-edit-this-page",
            ".table-of-contents", ".theme-doc-sidebar-container", ".navbar",
        ],
    },
    "gitbook": {
        "content": ".markdown-body, [data-testid='page.contentEditor'], .page-body",
        "sidebar": "nav.sidebar, [data-testid='table-of-contents']",
        "sidebar_links": "nav.sidebar a",
        "remove": [
            ".page-footer", "[data-testid='page.editButton']", ".header-row",
        ],
    },
    "readthedocs": {
        "content": ".document .body, .rst-content, [role='main']",
        "sidebar": ".wy-nav-side nav, .sphinxsidebar",
        "sidebar_links": ".wy-nav-side a, .sphinxsidebar a",
        "remove": [
            ".rst-footer-buttons", ".wy-breadcrumbs", ".headerlink", ".wy-nav-top",
        ],
    },
    "mkdocs": {
        "content": ".md-content article, .md-content__inner",
        "sidebar": ".md-sidebar--primary nav, .md-nav",
        "sidebar_links": ".md-nav__link",
        "remove": [
            ".md-footer", ".md-header", ".md-source", ".md-content__button",
        ],
    },
    "nextjs": {
        "content": "main article, main .content, #__next main",
        "sidebar": "nav[class*='sidebar'], aside nav",
        "sidebar_links": "nav[class*='sidebar'] a",
        "remove": [
            "footer", "header", "[class*='feedback']", "[class*='breadcrumb']",
        ],
    },
    "mintlify": {
        "content": "#content-area article, main article",
        "sidebar": "nav[class*='sidebar']",
        "sidebar_links": "nav[class*='sidebar'] a",
        "remove": [
            "[class*='Feedback']", "[class*='PageFooter']", "header",
        ],
    },
    "vuepress": {
        "content": ".theme-default-content, .content__default",
        "sidebar": ".sidebar-links, .sidebar",
        "sidebar_links": ".sidebar-link",
        "remove": [
            ".page-edit", ".page-nav", ".header-anchor",
        ],
    },
    "generic": {
        "content": "main article, article, [role='main'], main, .content, #content",
        "sidebar": "nav[class*='sidebar'], aside nav, .sidebar nav",
        "sidebar_links": "nav[class*='sidebar'] a, aside nav a, .sidebar nav a",
        "remove": [
            "footer", "header", "nav[class*='navbar']",
            "[class*='cookie']", "[class*='banner']",
        ],
    },
}


# ---------------------------------------------------------------------------
# Framework detection
# ---------------------------------------------------------------------------

def detect_framework(html: str) -> str:
    """Detect the documentation framework from raw HTML source."""
    html_lower = html.lower()

    if '<meta name="generator" content="docusaurus' in html_lower or "__docusaurus" in html_lower:
        return "docusaurus"
    if "gitbook" in html_lower and (".gitbook-root" in html_lower or "gitbook" in html_lower[:5000]):
        return "gitbook"
    if "readthedocs" in html_lower or ".rst-content" in html_lower:
        return "readthedocs"
    if re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']mkdocs', html_lower):
        return "mkdocs"
    if ".md-content" in html_lower and ".md-sidebar" in html_lower:
        return "mkdocs"
    if "mintlify" in html_lower:
        return "mintlify"
    if "vuepress" in html_lower or ".theme-default-content" in html_lower:
        return "vuepress"
    if 'id="__next"' in html_lower or "/_next/" in html_lower:
        return "nextjs"

    return "generic"


# ---------------------------------------------------------------------------
# Sidebar link extraction
# ---------------------------------------------------------------------------

def extract_sidebar_links(html: str, base_url: str, framework: str) -> List[str]:
    """Extract ordered navigation links from the documentation sidebar."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    selectors = FRAMEWORK_SELECTORS.get(framework, FRAMEWORK_SELECTORS["generic"])
    link_selector = selectors["sidebar_links"]

    seen = set()
    links: List[str] = []

    for element in soup.select(link_selector):
        href = element.get("href")
        if not href or href.startswith("#") or href.startswith("javascript:"):
            continue
        resolved = normalize_url(href, base_url)
        base_domain = urllib.parse.urlparse(base_url).netloc.split(":")[0]
        if not is_internal_link(resolved, base_domain):
            continue
        if resolved not in seen:
            seen.add(resolved)
            links.append(resolved)

    return links


# ---------------------------------------------------------------------------
# BFS fallback for when sidebar extraction yields nothing
# ---------------------------------------------------------------------------

def extract_all_links(html: str, base_url: str) -> List[str]:
    """Extract all internal links from an HTML page (BFS fallback)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    base_domain = urllib.parse.urlparse(base_url).netloc.split(":")[0]
    seen = set()
    links: List[str] = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#") or href.startswith("javascript:") or href.startswith("mailto:"):
            continue
        resolved = normalize_url(href, base_url)
        if is_internal_link(resolved, base_domain) and resolved not in seen:
            seen.add(resolved)
            links.append(resolved)

    return links


# ---------------------------------------------------------------------------
# Content cleaning (remove doc-specific noise before conversion)
# ---------------------------------------------------------------------------

def clean_doc_noise(html: str, framework: str) -> str:
    """Remove documentation-specific noise elements from HTML."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    selectors = FRAMEWORK_SELECTORS.get(framework, FRAMEWORK_SELECTORS["generic"])
    remove_selectors = selectors.get("remove", [])

    for sel in remove_selectors:
        for element in soup.select(sel):
            element.decompose()

    # Universal noise removal across all frameworks
    universal_noise = [
        "[class*='EditThisPage']", "[class*='edit-this-page']",
        "[class*='was-this-helpful']", "[class*='thumbs-up']",
        "[class*='page-feedback']", "[class*='version-selector']",
        "[class*='language-selector']", "[class*='prev-next']",
    ]
    for sel in universal_noise:
        for element in soup.select(sel):
            element.decompose()

    return str(soup)


# ---------------------------------------------------------------------------
# Page title extraction
# ---------------------------------------------------------------------------

def extract_title(markdown: str) -> str:
    """Extract title from markdown content."""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("title:"):
            return stripped.split(":", 1)[1].strip().strip('"')
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return ""


# ---------------------------------------------------------------------------
# Consolidation
# ---------------------------------------------------------------------------

def consolidate(output_dir: str, pages: List[Dict]) -> str:
    """Generate FULL_DOCS.md from all scraped pages in sidebar order."""
    lines: List[str] = ["# Full Documentation\n"]
    lines.append("## Table of Contents\n")

    for i, page in enumerate(pages, 1):
        title = page.get("title") or page.get("filename", "Untitled")
        lines.append(f"{i}. [{title}](#{_slugify(title)})")

    lines.append("\n")

    for page in pages:
        title = page.get("title") or page.get("filename", "Untitled")
        url = page.get("url", "")
        filepath = os.path.join(output_dir, page["filename"])
        if not os.path.isfile(filepath):
            continue

        with open(filepath, "r", encoding="utf-8") as fh:
            content = fh.read()

        # Strip frontmatter from individual pages
        content = re.sub(r"^---\n.*?\n---\n*", "", content, count=1, flags=re.DOTALL)
        content = content.strip()

        lines.append("---\n")
        lines.append(f"<!-- source: {url} -->\n")
        lines.append(f"# {title}\n")
        lines.append(content)
        lines.append("\n")

    return "\n".join(lines)


def _slugify(text: str) -> str:
    """Create a simple slug from text for markdown anchor links."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s]+", "-", slug)
    return slug


# ---------------------------------------------------------------------------
# INDEX.md generation
# ---------------------------------------------------------------------------

def generate_index_md(pages: List[Dict], base_url: str, framework: str) -> str:
    """Generate an INDEX.md with metadata about the scrape."""
    lines = [
        f"# Documentation Index",
        f"",
        f"- **Source**: {base_url}",
        f"- **Framework**: {framework}",
        f"- **Pages**: {len(pages)}",
        f"",
        f"## Pages",
        f"",
    ]
    for page in pages:
        title = page.get("title") or page.get("filename", "?")
        lines.append(f"- [{title}]({page['filename']}) — {page['url']}")

    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main scraping logic
# ---------------------------------------------------------------------------

def scrape_docs(args: argparse.Namespace) -> None:
    """Main documentation scraping pipeline."""
    start_url: str = args.url
    output_dir = setup_output_dir(args.output)
    session = create_session()
    index_path = os.path.join(str(output_dir), "index.json")

    # Resume support
    index_data: Dict = {}
    scraped_urls: set = set()
    if args.resume:
        index_data = load_index(index_path)
        scraped_urls = {entry["url"] for entry in index_data.get("pages", [])}
        if scraped_urls:
            print(f"Resuming: {len(scraped_urls)} pages already scraped", file=sys.stderr)

    # 1. Fetch start page
    html = _fetch_html(start_url, session, args)

    # 2. Detect framework
    framework = detect_framework(html)
    print(f"Detected framework: {framework.title()}", file=sys.stderr)

    # 3. Extract sidebar links
    sidebar_links = extract_sidebar_links(html, start_url, framework)

    use_bfs = len(sidebar_links) == 0
    if sidebar_links:
        print(f"Found {len(sidebar_links)} pages in sidebar navigation", file=sys.stderr)
        # Ensure start URL is included at the front
        if start_url not in sidebar_links:
            sidebar_links.insert(0, start_url)
        queue = sidebar_links[:args.max_pages]
    else:
        print("No sidebar found, falling back to BFS crawling", file=sys.stderr)
        queue = [start_url]

    # 4. Scrape pages
    pages: List[Dict] = list(index_data.get("pages", []))
    visited: set = set(scraped_urls)
    page_num = len(pages)
    total_label = len(queue) if not use_bfs else "?"

    while queue and page_num < args.max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)

        # Robots.txt check
        if not args.no_robots:
            allowed, reason = check_robots_txt(url, session)
            if not allowed:
                logger.info("Skipping %s: %s", url, reason)
                continue

        # Fetch
        try:
            page_html = _fetch_html(url, session, args) if url != start_url else html
            if url == start_url and page_num > 0:
                page_html = _fetch_html(url, session, args)
        except ScrapingError as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
            continue

        page_num += 1
        progress = f"[{page_num}/{total_label}]"

        # Clean doc noise
        cleaned_html = clean_doc_noise(page_html, framework)

        # Convert to markdown
        content_selector = args.selector or FRAMEWORK_SELECTORS.get(
            framework, FRAMEWORK_SELECTORS["generic"]
        )["content"]
        markdown = convert_html_to_markdown(
            cleaned_html, url=url,
            include_frontmatter=True,
            content_selector=content_selector,
        )

        title = extract_title(markdown)
        short_title = title[:50] if title else urllib.parse.urlparse(url).path
        print(f"{progress} Scraping: {short_title} ({urllib.parse.urlparse(url).path})", file=sys.stderr)

        # Save individual page
        filename = sanitize_filename(url)
        filepath = os.path.join(str(output_dir), filename)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(markdown)

        pages.append({
            "url": url,
            "title": title,
            "filename": filename,
        })

        # BFS: discover new links from this page
        if use_bfs:
            new_links = extract_all_links(page_html, url)
            for link in new_links:
                if link not in visited:
                    queue.append(link)

        # Politeness delay
        if args.delay > 0:
            time.sleep(args.delay)

    # 5. Save index.json
    save_index(index_path, {"base_url": start_url, "framework": framework, "pages": pages})

    # 6. Generate INDEX.md
    index_md = generate_index_md(pages, start_url, framework)
    index_md_path = os.path.join(str(output_dir), "INDEX.md")
    with open(index_md_path, "w", encoding="utf-8") as fh:
        fh.write(index_md)

    print(f"Done! {len(pages)} pages scraped to {output_dir}/", file=sys.stderr)

    # 7. Consolidate if requested
    if args.consolidate:
        full_doc = consolidate(str(output_dir), pages)
        full_path = os.path.join(str(output_dir), "FULL_DOCS.md")
        with open(full_path, "w", encoding="utf-8") as fh:
            fh.write(full_doc)
        size_kb = len(full_doc.encode("utf-8")) / 1024
        print(f"Consolidated document: {full_path} ({size_kb:.0f} KB)", file=sys.stderr)


def _fetch_html(url: str, session, args: argparse.Namespace) -> str:
    """Fetch HTML for a URL, using Playwright if needed."""
    html, status = fetch_page(url, session=session, retries=args.retries, timeout=30)

    if args.javascript:
        html = render_with_playwright(url, timeout=30000)
    elif detect_dynamic_content(html):
        logger.info("Dynamic content detected on %s, using Playwright", url)
        html = render_with_playwright(url, timeout=30000)

    return html


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Scrape documentation sites with framework-aware intelligence.",
    )
    p.add_argument("url", help="Documentation site URL to scrape.")
    p.add_argument("-o", "--output", default="./docs_output", metavar="DIR",
                   help="Output directory (default: ./docs_output).")
    p.add_argument("-m", "--max-pages", type=int, default=200, metavar="N",
                   help="Maximum number of pages to scrape (default: 200).")
    p.add_argument("-j", "--javascript", action="store_true",
                   help="Force JavaScript rendering via Playwright.")
    p.add_argument("-c", "--consolidate", action="store_true",
                   help="Generate a single FULL_DOCS.md with all pages.")
    p.add_argument("-s", "--selector", default=None, metavar="CSS",
                   help="Override CSS selector for main content area.")
    p.add_argument("--delay", type=float, default=1.0,
                   help="Delay in seconds between requests (default: 1.0).")
    p.add_argument("--no-robots", action="store_true",
                   help="Skip robots.txt compliance checks.")
    p.add_argument("--resume", action="store_true",
                   help="Resume a previous incomplete scrape.")
    p.add_argument("--retries", type=int, default=3,
                   help="Number of retry attempts per page (default: 3).")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        scrape_docs(args)
    except ScrapingError as exc:
        logger.error("Scraping failed: %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
