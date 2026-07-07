#!/usr/bin/env python3
"""
Single-page scraper: fetch a URL and convert it to Markdown.

Uses utils.py for HTTP/robots/rendering and html_to_markdown.py for conversion.

Usage:
    python3 scrape_page.py "https://example.com/docs" -o docs.md
    python3 scrape_page.py "https://spa-site.com" -j --wait-for ".content" -o page.md
    python3 scrape_page.py "https://docs.site.com/api" -s ".api-docs" -o api.md
"""

import argparse
import logging
import os
import sys

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
    render_with_playwright,
)
from html_to_markdown import convert_html_to_markdown

logger = logging.getLogger("scrape_page")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Fetch a single web page and convert it to Markdown.",
    )
    p.add_argument("url", help="URL to scrape.")
    p.add_argument("-o", "--output", default=None, metavar="FILE",
                   help="Write Markdown to FILE instead of stdout.")
    p.add_argument("-s", "--selector", default=None, metavar="CSS",
                   help="CSS selector for the main content area.")
    p.add_argument("-j", "--javascript", action="store_true",
                   help="Force JavaScript rendering via Playwright.")
    p.add_argument("--wait-for", default=None, metavar="SEL",
                   help="CSS selector to wait for when using Playwright.")
    p.add_argument("--timeout", type=int, default=30,
                   help="HTTP request timeout in seconds (default: 30).")
    p.add_argument("--no-robots", action="store_true",
                   help="Skip robots.txt check.")
    p.add_argument("--no-frontmatter", action="store_true",
                   help="Omit YAML frontmatter from output.")
    p.add_argument("--retries", type=int, default=3,
                   help="Number of retry attempts (default: 3).")
    return p


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def scrape(args: argparse.Namespace) -> str:
    """Run the scrape pipeline and return the Markdown string."""
    url: str = args.url
    session = create_session()

    # 1. Robots.txt -----------------------------------------------------------
    if not args.no_robots:
        allowed, reason = check_robots_txt(url, session)
        if not allowed:
            raise ScrapingError(f"Blocked by robots.txt: {reason}", url=url)
        logger.info("robots.txt: access allowed")

    # 2. Fetch page -----------------------------------------------------------
    html, status = fetch_page(url, session=session, retries=args.retries,
                              timeout=args.timeout)
    logger.info("Fetched %s [HTTP %d] (%d bytes)", url, status, len(html))

    # 3. Decide whether to use JS rendering -----------------------------------
    used_js = False
    if args.javascript:
        logger.info("JavaScript rendering forced by --javascript flag")
        html = render_with_playwright(url, wait_for=args.wait_for,
                                      timeout=args.timeout * 1000)
        used_js = True
    elif detect_dynamic_content(html):
        logger.info("Dynamic content detected — falling back to Playwright")
        html = render_with_playwright(url, wait_for=args.wait_for,
                                      timeout=args.timeout * 1000)
        used_js = True

    # 4. Convert to Markdown --------------------------------------------------
    markdown = convert_html_to_markdown(
        html,
        url=url,
        include_frontmatter=not args.no_frontmatter,
        content_selector=args.selector,
    )

    # 5. Extract title for the summary ----------------------------------------
    title = ""
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("title:"):
            title = stripped.split(":", 1)[1].strip().strip('"')
            break
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break

    # 6. Write output ---------------------------------------------------------
    if args.output:
        out_dir = os.path.dirname(args.output)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(markdown)
        logger.info("Wrote %s", args.output)

    # 7. Print summary to stderr ---------------------------------------------
    size = len(markdown.encode("utf-8"))
    print(f"URL:        {url}", file=sys.stderr)
    if title:
        print(f"Title:      {title}", file=sys.stderr)
    print(f"Size:       {size:,} bytes", file=sys.stderr)
    print(f"JS render:  {'yes' if used_js else 'no'}", file=sys.stderr)
    if args.output:
        print(f"Output:     {args.output}", file=sys.stderr)

    return markdown


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        markdown = scrape(args)
        # If no output file was given, print to stdout
        if not args.output:
            sys.stdout.write(markdown)
    except ScrapingError as exc:
        logger.error("Scraping failed: %s", exc)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as exc:
        logger.error("Unexpected error: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
