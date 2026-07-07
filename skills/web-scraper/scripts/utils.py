"""
Shared utilities module for web scraping.

Provides HTTP session management, URL handling, robots.txt compliance,
dynamic content detection, and file I/O helpers.

Dependencies: requests, beautifulsoup4 (+ standard library)
"""

import json
import logging
import os
import pathlib
import re
import subprocess
import tempfile
import time
import urllib.parse
import urllib.robotparser
from typing import Dict, Optional, Tuple

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Custom Exception
# ---------------------------------------------------------------------------


class ScrapingError(Exception):
    """Raised when a scraping operation fails after all retries."""

    def __init__(self, message: str, url: str = "", status_code: int = 0):
        self.url = url
        self.status_code = status_code
        super().__init__(message)


# ---------------------------------------------------------------------------
# HTTP Session
# ---------------------------------------------------------------------------

_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_DEFAULT_HEADERS = {
    "User-Agent": _DEFAULT_USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def create_session() -> requests.Session:
    """Create an HTTP session with realistic headers and connection pooling.

    Returns:
        A ``requests.Session`` pre-configured with browser-like headers and
        a connection-pool adapter mounted for both HTTP and HTTPS.
    """
    session = requests.Session()
    session.headers.update(_DEFAULT_HEADERS)

    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=20,
        max_retries=0,  # We handle retries manually in fetch_page
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    logger.debug("Created new HTTP session with connection pooling")
    return session


# ---------------------------------------------------------------------------
# Page Fetching
# ---------------------------------------------------------------------------


def _detect_encoding(response: requests.Response) -> Optional[str]:
    """Try to detect the correct encoding from headers and HTML meta tags.

    Checks the Content-Type header first, then falls back to scanning the
    response body for ``<meta charset="...">`` or
    ``<meta http-equiv="Content-Type" ...>`` declarations.
    """
    # 1. Content-Type header
    content_type = response.headers.get("Content-Type", "")
    match = re.search(r"charset=([^\s;]+)", content_type, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 2. HTML meta charset (scan first 4 KB of raw bytes)
    head_bytes = response.content[:4096]
    try:
        head_text = head_bytes.decode("ascii", errors="ignore")
    except Exception:
        head_text = ""

    # <meta charset="utf-8">
    match = re.search(r'<meta[^>]+charset=["\']?([^"\'\s;>]+)', head_text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    match = re.search(
        r'<meta[^>]+http-equiv=["\']?Content-Type["\']?[^>]+charset=([^\s"\'>;]+)',
        head_text,
        re.IGNORECASE,
    )
    if match:
        return match.group(1).strip()

    return None


def fetch_page(
    url: str,
    session: requests.Session = None,
    retries: int = 3,
    timeout: int = 30,
) -> Tuple[str, int]:
    """Fetch a page with exponential back-off on transient errors.

    Back-off schedule: 2 s, 4 s, 8 s, 16 s (doubling each attempt).
    Retries are triggered by HTTP 429 (rate-limit) and 5xx (server errors).

    Args:
        url: The URL to fetch.
        session: An optional ``requests.Session``. A temporary one is created
            if *None*.
        retries: Maximum number of retry attempts (default 3).
        timeout: Request timeout in seconds (default 30).

    Returns:
        A tuple ``(html_content, status_code)``.

    Raises:
        ScrapingError: After all retry attempts have been exhausted.
    """
    if session is None:
        session = create_session()

    last_error: Optional[Exception] = None
    last_status: int = 0

    for attempt in range(retries + 1):
        try:
            logger.info("Fetching %s (attempt %d/%d)", url, attempt + 1, retries + 1)
            response = session.get(url, timeout=timeout, allow_redirects=True)
            last_status = response.status_code

            # Success
            if response.status_code < 400:
                encoding = _detect_encoding(response)
                if encoding:
                    response.encoding = encoding
                logger.debug(
                    "Fetched %s  [%d] encoding=%s",
                    url,
                    response.status_code,
                    response.encoding,
                )
                return response.text, response.status_code

            # Retryable status codes
            if response.status_code == 429 or response.status_code >= 500:
                backoff = 2 ** (attempt + 1)  # 2, 4, 8, 16 ...
                logger.warning(
                    "Received %d from %s -- retrying in %ds",
                    response.status_code,
                    url,
                    backoff,
                )
                time.sleep(backoff)
                continue

            # Non-retryable client error (4xx except 429)
            raise ScrapingError(
                f"HTTP {response.status_code} for {url}",
                url=url,
                status_code=response.status_code,
            )

        except ScrapingError:
            raise
        except requests.RequestException as exc:
            last_error = exc
            backoff = 2 ** (attempt + 1)
            logger.warning(
                "Request error for %s: %s -- retrying in %ds",
                url,
                exc,
                backoff,
            )
            time.sleep(backoff)

    # All retries exhausted
    msg = f"Failed to fetch {url} after {retries + 1} attempts"
    if last_error:
        msg += f": {last_error}"
    raise ScrapingError(msg, url=url, status_code=last_status)


# ---------------------------------------------------------------------------
# Robots.txt
# ---------------------------------------------------------------------------

_robots_cache: Dict[str, urllib.robotparser.RobotFileParser] = {}


def check_robots_txt(
    url: str,
    session: requests.Session = None,
) -> Tuple[bool, str]:
    """Check whether *url* is allowed by the site's ``robots.txt``.

    Results are cached per domain so repeated calls for the same site are
    essentially free.

    Args:
        url: The target URL to check.
        session: Optional HTTP session (used only to share the User-Agent
            string; the actual fetch is done by ``urllib.robotparser``).

    Returns:
        A tuple ``(is_allowed, reason)`` where *reason* is an empty string
        when access is allowed, or a human-readable explanation when blocked.
    """
    parsed = urllib.parse.urlparse(url)
    domain = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{domain}/robots.txt"

    user_agent = _DEFAULT_USER_AGENT
    if session and "User-Agent" in session.headers:
        user_agent = session.headers["User-Agent"]

    if domain not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        try:
            rp.read()
            logger.debug("Loaded robots.txt from %s", robots_url)
        except Exception as exc:
            # If we cannot fetch robots.txt, assume allowed
            logger.warning("Could not fetch %s: %s -- assuming allowed", robots_url, exc)
            return True, ""
        _robots_cache[domain] = rp

    rp = _robots_cache[domain]
    if rp.can_fetch(user_agent, url):
        return True, ""

    reason = f"Blocked by robots.txt at {robots_url} for user-agent '{user_agent}'"
    logger.info("robots.txt disallows %s", url)
    return False, reason


# ---------------------------------------------------------------------------
# URL Utilities
# ---------------------------------------------------------------------------


def normalize_url(url: str, base_url: str) -> str:
    """Resolve and normalise a URL against a base.

    * Resolves relative paths against *base_url*.
    * Handles protocol-relative URLs (``//example.com/...``).
    * Strips fragment identifiers (``#...``).
    * Removes trailing slashes for consistency.

    Args:
        url: The raw URL (may be relative or absolute).
        base_url: The page URL used as the resolution base.

    Returns:
        A fully-qualified, normalised URL string.
    """
    url = url.strip()

    # Protocol-relative URLs
    if url.startswith("//"):
        scheme = urllib.parse.urlparse(base_url).scheme or "https"
        url = f"{scheme}:{url}"

    # Resolve against base
    resolved = urllib.parse.urljoin(base_url, url)

    # Parse, drop fragment, rebuild
    parts = urllib.parse.urlparse(resolved)
    cleaned = urllib.parse.urlunparse(
        (parts.scheme, parts.netloc, parts.path, parts.params, parts.query, "")
    )

    # Remove trailing slash (but keep root "/" as-is)
    if cleaned.endswith("/") and len(cleaned) > len(f"{parts.scheme}://{parts.netloc}/"):
        cleaned = cleaned.rstrip("/")

    return cleaned


def is_internal_link(url: str, base_domain: str) -> bool:
    """Determine whether *url* belongs to *base_domain* (including subdomains).

    Args:
        url: A fully-qualified URL.
        base_domain: The reference domain, e.g. ``example.com``.

    Returns:
        ``True`` if the URL's host matches *base_domain* or is a subdomain
        of it; ``False`` otherwise.
    """
    parsed = urllib.parse.urlparse(url)
    host = parsed.netloc.lower().split(":")[0]  # strip port
    base_domain = base_domain.lower().strip(".")

    return host == base_domain or host.endswith(f".{base_domain}")


# ---------------------------------------------------------------------------
# Filename Helpers
# ---------------------------------------------------------------------------

_UNSAFE_CHARS = re.compile(r"[^\w\-.]")
_MAX_FILENAME_LENGTH = 200


def sanitize_filename(url: str, base_url: str = None) -> str:
    """Convert a URL path into a safe, readable filename ending in ``.md``.

    Examples::

        /docs/api/overview  ->  docs_api_overview.md
        /                   ->  index.md
        /blog/my-post?v=2   ->  blog_my-post.md

    Args:
        url: The URL (or path) to convert.
        base_url: Optional base URL used to extract only the path portion
            when *url* is absolute.

    Returns:
        A filesystem-safe filename string.
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path

    # Strip leading/trailing slashes
    path = path.strip("/")

    if not path:
        return "index.md"

    # Replace path separators with underscores
    name = path.replace("/", "_")

    # Remove unsafe characters
    name = _UNSAFE_CHARS.sub("_", name)

    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name).strip("_")

    # Enforce length limit (reserve space for .md)
    if len(name) > _MAX_FILENAME_LENGTH - 3:
        name = name[: _MAX_FILENAME_LENGTH - 3]

    # Ensure .md extension
    if not name.endswith(".md"):
        # Remove any existing extension so we get a clean .md
        if "." in name.rsplit("_", 1)[-1]:
            name = name.rsplit(".", 1)[0]
        name = f"{name}.md"

    return name


# ---------------------------------------------------------------------------
# Dynamic Content Detection
# ---------------------------------------------------------------------------

_DYNAMIC_PATTERNS = [
    # React
    re.compile(r'<div\s+id=["\'](?:root|app|__next)["\']>\s*</div>', re.IGNORECASE),
    re.compile(r'<div\s+id=["\'](?:root|app|__next)["\']\s*/>', re.IGNORECASE),
    # Next.js
    re.compile(r"__NEXT_DATA__", re.IGNORECASE),
    # Angular
    re.compile(r"<app-root[^>]*>\s*</app-root>", re.IGNORECASE),
    # Generic SPA signals
    re.compile(r"<noscript[^>]*>.*?(?:enable|requires?|needs?)\s+javascript", re.IGNORECASE | re.DOTALL),
    # Large JS bundles (common SPA indicator)
    re.compile(r'<script[^>]+src=["\'][^"\']*bundle[^"\']*\.js["\']', re.IGNORECASE),
    re.compile(r'<script[^>]+src=["\'][^"\']*main\.[a-f0-9]+\.js["\']', re.IGNORECASE),
    # Vue
    re.compile(r'<div\s+id=["\']app["\']>\s*</div>', re.IGNORECASE),
    # Svelte / generic
    re.compile(r'<div\s+id=["\']svelte["\']', re.IGNORECASE),
]


def detect_dynamic_content(html: str) -> bool:
    """Heuristically detect whether an HTML page relies on client-side rendering.

    Checks for common SPA patterns such as empty root ``<div>`` elements,
    ``__NEXT_DATA__`` scripts, ``<noscript>`` warnings, and large JS bundle
    references.

    Args:
        html: The raw HTML string to analyse.

    Returns:
        ``True`` if the page likely requires JavaScript rendering.
    """
    # Quick check: very small body text is suspicious
    soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body")
    if body:
        body_text = body.get_text(separator=" ", strip=True)
        # An almost-empty body with scripts is a strong SPA signal
        scripts = body.find_all("script")
        if len(body_text) < 100 and len(scripts) > 2:
            logger.debug("Dynamic content detected: near-empty body with %d scripts", len(scripts))
            return True

    for pattern in _DYNAMIC_PATTERNS:
        if pattern.search(html):
            logger.debug("Dynamic content detected via pattern: %s", pattern.pattern[:60])
            return True

    return False


# ---------------------------------------------------------------------------
# Playwright Rendering
# ---------------------------------------------------------------------------

_RENDER_SCRIPT = pathlib.Path(__file__).parent / "render_page.js"


def render_with_playwright(
    url: str,
    wait_for: str = None,
    timeout: int = 30000,
) -> str:
    """Render a page using Playwright via the companion ``render_page.js`` script.

    Args:
        url: The page URL to render.
        wait_for: Optional CSS selector to wait for before capturing HTML.
        timeout: Playwright navigation timeout in milliseconds (default 30 000).

    Returns:
        The fully-rendered HTML string.

    Raises:
        ScrapingError: If Playwright is not installed or rendering fails.
    """
    if not _RENDER_SCRIPT.exists():
        raise ScrapingError(
            f"Render script not found at {_RENDER_SCRIPT}. "
            "Ensure render_page.js is present in the scripts/ directory.",
            url=url,
        )

    cmd = ["node", str(_RENDER_SCRIPT), url, "--timeout", str(timeout)]
    if wait_for:
        cmd.extend(["--wait-for", wait_for])

    logger.info("Rendering %s with Playwright (timeout=%dms)", url, timeout)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout / 1000 + 15,  # generous process-level timeout
        )
    except FileNotFoundError:
        raise ScrapingError(
            "Node.js is not installed or not on PATH. "
            "Playwright rendering requires Node.js >= 18.",
            url=url,
        )
    except subprocess.TimeoutExpired:
        raise ScrapingError(
            f"Playwright rendering timed out after {timeout}ms for {url}",
            url=url,
        )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        if "playwright" in stderr.lower() and ("install" in stderr.lower() or "not found" in stderr.lower()):
            raise ScrapingError(
                "Playwright is not installed. Run: npx playwright install chromium",
                url=url,
            )
        raise ScrapingError(
            f"Playwright render failed for {url}: {stderr}",
            url=url,
            status_code=result.returncode,
        )

    html = result.stdout
    if not html.strip():
        raise ScrapingError(
            f"Playwright returned empty HTML for {url}",
            url=url,
        )

    logger.debug("Playwright rendered %d characters for %s", len(html), url)
    return html


# ---------------------------------------------------------------------------
# File I/O Helpers
# ---------------------------------------------------------------------------


def setup_output_dir(path: str) -> pathlib.Path:
    """Create the output directory tree if it does not already exist.

    Args:
        path: The desired output directory (may be nested).

    Returns:
        A ``pathlib.Path`` pointing to the created directory.
    """
    out = pathlib.Path(path)
    out.mkdir(parents=True, exist_ok=True)
    logger.debug("Output directory ready: %s", out)
    return out


def load_index(index_path: str) -> dict:
    """Load an ``index.json`` file for resume functionality.

    If the file does not exist or is malformed, an empty dictionary is
    returned so callers can always treat the result as a valid mapping.

    Args:
        index_path: Path to the JSON index file.

    Returns:
        A dictionary with the previously-saved index data, or ``{}`` on
        any error.
    """
    p = pathlib.Path(index_path)
    if not p.exists():
        logger.debug("Index file not found at %s -- starting fresh", index_path)
        return {}

    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            logger.warning("Index at %s is not a dict -- ignoring", index_path)
            return {}
        logger.debug("Loaded index with %d entries from %s", len(data), index_path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load index from %s: %s", index_path, exc)
        return {}


def save_index(index_path: str, data: dict) -> None:
    """Save an ``index.json`` file atomically.

    Writes to a temporary file in the same directory first, then renames it
    so that a crash mid-write never corrupts the index.

    Args:
        index_path: Destination path for the JSON index.
        data: The dictionary to persist.
    """
    p = pathlib.Path(index_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: temp file in same dir, then rename
    fd, tmp_path = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_path, str(p))
        logger.debug("Saved index with %d entries to %s", len(data), index_path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
