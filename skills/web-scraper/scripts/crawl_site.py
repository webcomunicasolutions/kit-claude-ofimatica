#!/usr/bin/env python3
"""
BFS Site Crawler -- discovers and scrapes pages into Markdown files.

Usage:
    crawl_site.py <url> [-o dir] [-d 3] [-m 100] [--delay 1.0] [-p pattern]
                        [-s selector] [-j] [--no-robots] [--resume] [--retries 3]
"""

import argparse
import os
import re
import sys
import time
import urllib.parse
from collections import deque
from datetime import datetime, timezone

# Ensure sibling imports work regardless of caller's working directory.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

from utils import (
    ScrapingError, check_robots_txt, create_session, detect_dynamic_content,
    fetch_page, is_internal_link, load_index, normalize_url,
    render_with_playwright, sanitize_filename, save_index, setup_output_dir,
)
from html_to_markdown import convert_html_to_markdown

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 required. pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)

_SKIP_EXT = re.compile(
    r"\.(pdf|png|jpe?g|gif|svg|ico|webp|bmp|tiff?"
    r"|zip|tar|gz|bz2|rar|7z|mp[34]|avi|mov|wmv|flv|webm|ogg|wav"
    r"|exe|dmg|msi|deb|rpm|doc|docx|xls|xlsx|ppt|pptx|csv)$",
    re.IGNORECASE,
)
_SKIP_SCHEMES = {"mailto:", "javascript:", "tel:", "data:", "ftp:"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Link extraction
# ---------------------------------------------------------------------------

def extract_links(html, page_url, base_domain, pattern=None):
    """Yield unique, normalised, internal URLs found in *html*."""
    soup = BeautifulSoup(html, "html.parser")
    seen = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if any(href.lower().startswith(s) for s in _SKIP_SCHEMES):
            continue
        url = normalize_url(href, page_url)
        if not url.startswith(("http://", "https://")):
            continue
        if _SKIP_EXT.search(urllib.parse.urlparse(url).path):
            continue
        if not is_internal_link(url, base_domain):
            continue
        if pattern and not pattern.search(url):
            continue
        if url not in seen:
            seen.add(url)
            yield url


# ---------------------------------------------------------------------------
# INDEX.md generation
# ---------------------------------------------------------------------------

def _build_index_md(index_data, output_dir):
    """Write INDEX.md table of contents from current index data."""
    base_url = index_data.get("base_url", "")
    domain = urllib.parse.urlparse(base_url).netloc or base_url
    pages = index_data.get("pages", {})
    ok = {u: p for u, p in pages.items() if p.get("status") == "success"}
    started = index_data.get("started_at", "")[:10]

    lines = [
        f"# Site Map: {domain}", "",
        f"Crawled on {started}. {len(ok)} pages scraped.", "",
        "## Pages", "",
    ]
    for url, info in sorted(ok.items(), key=lambda x: x[1].get("depth", 0)):
        title = info.get("title") or info.get("file", "")
        path = urllib.parse.urlparse(url).path or "/"
        lines.append(f"- [{title}]({info.get('file', '')}) - {path}")
    lines.append("")

    with open(os.path.join(output_dir, "INDEX.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------------
# Page record helper
# ---------------------------------------------------------------------------

def _page_record(filename="", title="", status="success", depth=0):
    return {
        "file": filename, "title": title, "status": status,
        "scraped_at": _now_iso(), "depth": depth,
    }


# ---------------------------------------------------------------------------
# Main crawl loop
# ---------------------------------------------------------------------------

def crawl(args):
    start_url = args.url.rstrip("/")
    base_domain = urllib.parse.urlparse(start_url).netloc.split(":")[0]
    output_dir = str(setup_output_dir(args.output))
    index_path = os.path.join(output_dir, "index.json")
    pattern = re.compile(args.pattern) if args.pattern else None

    # Initialise or resume
    index_data, visited, queue = {}, set(), deque()

    if args.resume:
        index_data = load_index(index_path)

    if index_data:
        visited = set(index_data.get("pages", {}).keys())
        for u in index_data.get("queue", []):
            if u not in visited:
                queue.append((u, 0))
        print(f"Resuming: {len(visited)} scraped, {len(queue)} queued", file=sys.stderr)
    else:
        index_data = {
            "base_url": start_url, "started_at": _now_iso(),
            "updated_at": _now_iso(), "pages": {}, "queue": [],
        }

    if not queue and start_url not in visited:
        queue.append((start_url, 0))

    session = create_session()
    n_ok = sum(1 for p in index_data.get("pages", {}).values() if p.get("status") == "success")

    while queue and n_ok < args.max_pages:
        url, depth = queue.popleft()
        if url in visited or depth > args.depth:
            continue

        # Robots.txt
        if not args.no_robots:
            allowed, _ = check_robots_txt(url, session)
            if not allowed:
                print(f"  Blocked by robots.txt: {url}", file=sys.stderr)
                visited.add(url)
                index_data["pages"][url] = _page_record(status="blocked_robots", depth=depth)
                continue

        n_ok += 1
        print(f"[{n_ok}/{args.max_pages}] Scraping {url} (depth: {depth})", file=sys.stderr)

        try:
            html, status = fetch_page(url, session, retries=args.retries, timeout=30)

            # Optionally render dynamic content with Playwright
            if args.javascript and detect_dynamic_content(html):
                print("  Dynamic content detected, rendering with Playwright...", file=sys.stderr)
                html = render_with_playwright(url)

            md = convert_html_to_markdown(
                html, url=url, include_frontmatter=True, content_selector=args.selector,
            )

            # Extract title from frontmatter or first heading
            title = ""
            m = re.search(r'^title:\s*"(.+?)"', md, re.MULTILINE)
            if m:
                title = m.group(1)
            if not title:
                m = re.search(r"^#\s+(.+)$", md, re.MULTILINE)
                if m:
                    title = m.group(1).strip()

            filename = sanitize_filename(url, start_url)
            with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
                f.write(md)

            visited.add(url)
            index_data["pages"][url] = _page_record(filename, title, "success", depth)

            # Discover and enqueue child links
            if depth < args.depth:
                for link in extract_links(html, url, base_domain, pattern):
                    if link not in visited:
                        queue.append((link, depth + 1))

        except (ScrapingError, Exception) as exc:
            label = "Error" if isinstance(exc, ScrapingError) else "Unexpected error"
            print(f"  {label}: {exc}", file=sys.stderr)
            visited.add(url)
            index_data["pages"][url] = _page_record(status=f"error: {exc}", depth=depth)

        # Persist after every page for resume robustness
        index_data["updated_at"] = _now_iso()
        index_data["queue"] = [u for u, _ in queue if u not in visited]
        save_index(index_path, index_data)

        if queue:
            time.sleep(args.delay)

    # Write final INDEX.md and summary
    _build_index_md(index_data, output_dir)
    pages = index_data["pages"]
    n_success = sum(1 for p in pages.values() if p.get("status") == "success")
    n_errors = sum(1 for p in pages.values() if p.get("status", "").startswith("error"))
    print(f"\nDone. {n_success} pages scraped, {n_errors} errors.", file=sys.stderr)
    print(f"Output: {output_dir}/", file=sys.stderr)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="BFS site crawler -- pages to Markdown.")
    ap.add_argument("url", help="Starting URL to crawl.")
    ap.add_argument("-o", "--output", default="output", help="Output directory (default: output).")
    ap.add_argument("-d", "--depth", type=int, default=3, help="Max crawl depth (default: 3).")
    ap.add_argument("-m", "--max-pages", type=int, default=100, help="Max pages to scrape (default: 100).")
    ap.add_argument("--delay", type=float, default=1.0, help="Delay in seconds between requests (default: 1.0).")
    ap.add_argument("-p", "--pattern", default=None, help="Regex filter for URLs.")
    ap.add_argument("-s", "--selector", default=None, help="CSS selector for main content.")
    ap.add_argument("-j", "--javascript", action="store_true", help="Render dynamic pages with Playwright.")
    ap.add_argument("--no-robots", action="store_true", help="Ignore robots.txt.")
    ap.add_argument("--resume", action="store_true", help="Resume previous crawl from index.json.")
    ap.add_argument("--retries", type=int, default=3, help="Retries per page (default: 3).")
    args = ap.parse_args()

    parsed = urllib.parse.urlparse(args.url)
    if not parsed.scheme or not parsed.netloc:
        ap.error(f"Invalid URL: {args.url}. Use a full URL like https://example.com")

    crawl(args)


if __name__ == "__main__":
    main()
