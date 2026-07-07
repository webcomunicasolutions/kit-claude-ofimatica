#!/usr/bin/env python3
"""
HTML to Markdown Converter

Converts HTML content to clean Markdown using only BeautifulSoup4.
No external markdown conversion libraries required.

Usage as module:
    from html_to_markdown import convert_html_to_markdown
    md = convert_html_to_markdown(html_string, url="https://example.com")

Usage as CLI:
    python3 html_to_markdown.py < input.html
    python3 html_to_markdown.py --url https://example.com < input.html
    python3 html_to_markdown.py --no-frontmatter < input.html
    python3 html_to_markdown.py --selector ".docs-content" < input.html
"""

import re
import sys
import argparse
from datetime import datetime, timezone
from typing import Optional

try:
    from bs4 import BeautifulSoup, NavigableString, Tag, Comment
except ImportError:
    print("Error: BeautifulSoup4 is required. Install with: pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TAGS_TO_REMOVE = {
    "script", "style", "nav", "footer", "header", "noscript",
    "iframe", "svg", "form", "button", "input", "select", "textarea",
}

CLASSES_TO_REMOVE = {
    "cookie", "banner", "popup", "modal", "overlay", "sidebar",
    "advertisement", "ad-", "ads-", "advert", "social-share",
    "share-buttons", "newsletter", "subscribe", "related-posts",
    "comments", "comment-", "footer", "nav", "menu", "breadcrumb",
    "toc", "table-of-contents",
}

MAIN_CONTENT_SELECTORS = [
    "main",
    "article",
    "[role='main']",
    ".markdown-body",
    ".docs-content",
    ".content",
    "#content",
    ".post-content",
    ".article-content",
    ".entry-content",
    ".page-content",
    "#main-content",
    ".main-content",
]

INLINE_TAGS = {"a", "abbr", "b", "strong", "i", "em", "code", "span", "small",
               "sub", "sup", "del", "s", "strike", "mark", "u", "kbd", "var"}


# ---------------------------------------------------------------------------
# Parser helpers
# ---------------------------------------------------------------------------

def _get_parser(html: str):
    """Try lxml first, fall back to html5lib, then html.parser."""
    for parser in ("lxml", "html5lib", "html.parser"):
        try:
            soup = BeautifulSoup(html, parser)
            return soup
        except Exception:
            continue
    # Absolute fallback – should never happen
    return BeautifulSoup(html, "html.parser")


def _detect_encoding(raw_bytes: bytes) -> str:
    """Detect encoding from meta charset in raw bytes."""
    snippet = raw_bytes[:4096].decode("ascii", errors="ignore").lower()
    # <meta charset="utf-8">
    m = re.search(r'<meta[^>]+charset=["\']?([^"\'\s;>]+)', snippet)
    if m:
        return m.group(1).strip()
    # <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    m = re.search(r'content=["\'][^"\']*charset=([^"\'\s;]+)', snippet)
    if m:
        return m.group(1).strip()
    return "utf-8"


def decode_html(raw: bytes | str) -> str:
    """Ensure we have a proper str from bytes or str input."""
    if isinstance(raw, str):
        return raw
    encoding = _detect_encoding(raw)
    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return raw.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_metadata(soup: BeautifulSoup, url: Optional[str] = None) -> dict:
    """Extract page metadata from a BeautifulSoup object.

    Returns a dict with keys: title, description, url, language.
    """
    # Title: prefer og:title, then <title>, then first <h1>
    title = None
    og_title = soup.find("meta", attrs={"property": "og:title"})
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    if not title:
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            title = title_tag.get_text(strip=True)
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

    # Description
    description = None
    og_desc = soup.find("meta", attrs={"property": "og:description"})
    if og_desc and og_desc.get("content"):
        description = og_desc["content"].strip()
    if not description:
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()

    # Language
    language = None
    html_tag = soup.find("html")
    if html_tag:
        language = html_tag.get("lang") or html_tag.get("xml:lang")
    if not language:
        meta_lang = soup.find("meta", attrs={"http-equiv": "content-language"})
        if meta_lang and meta_lang.get("content"):
            language = meta_lang["content"].strip()

    return {
        "title": title or "",
        "description": description or "",
        "url": url or "",
        "language": language or "",
    }


# ---------------------------------------------------------------------------
# HTML cleaning
# ---------------------------------------------------------------------------

def _should_remove_element(tag: Tag) -> bool:
    """Decide whether an element should be stripped based on tag name or class/id."""
    if tag.name in TAGS_TO_REMOVE:
        return True
    classes = " ".join(tag.get("class", [])).lower()
    tag_id = (tag.get("id") or "").lower()
    combined = classes + " " + tag_id
    for pattern in CLASSES_TO_REMOVE:
        if pattern in combined:
            return True
    # Detect hidden elements
    style = (tag.get("style") or "").lower()
    if "display:none" in style.replace(" ", "") or "visibility:hidden" in style.replace(" ", ""):
        return True
    # aria-hidden
    if tag.get("aria-hidden") == "true" and tag.name not in ("code", "pre"):
        return True
    return False


def _clean_html(soup: BeautifulSoup) -> BeautifulSoup:
    """Remove unwanted elements from the soup."""
    # Remove comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # Remove unwanted tags iteratively (list() to avoid mutation during iteration)
    for tag in list(soup.find_all(True)):
        if tag.parent is None:
            continue  # already removed
        if _should_remove_element(tag):
            tag.decompose()

    return soup


def _find_main_content(soup: BeautifulSoup, content_selector: Optional[str] = None) -> Tag:
    """Locate the main content area of the page."""
    # Custom selector first
    if content_selector:
        result = soup.select_one(content_selector)
        if result:
            return result

    # Try known selectors
    for selector in MAIN_CONTENT_SELECTORS:
        result = soup.select_one(selector)
        if result and len(result.get_text(strip=True)) > 100:
            return result

    # Fallback: <body> or entire soup
    body = soup.find("body")
    return body if body else soup


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _get_language_from_class(tag: Tag) -> str:
    """Extract programming language hint from class attribute."""
    classes = tag.get("class", [])
    for cls in classes:
        cls_lower = cls.lower()
        # language-python, lang-python, highlight-python
        for prefix in ("language-", "lang-", "highlight-"):
            if cls_lower.startswith(prefix):
                return cls_lower[len(prefix):]
        # sourceCode + specific class
        if cls_lower in (
            "python", "javascript", "js", "typescript", "ts", "java", "cpp",
            "c", "csharp", "cs", "go", "rust", "ruby", "php", "bash", "sh",
            "shell", "sql", "html", "css", "json", "yaml", "yml", "xml",
            "kotlin", "swift", "r", "perl", "lua", "scala", "haskell",
            "elixir", "clojure", "dart", "dockerfile", "makefile", "toml",
            "ini", "graphql", "markdown", "md", "plaintext", "text",
        ):
            return cls_lower
    return ""


def _convert_tag(tag, list_depth=0, ordered_counters=None):
    """Recursively convert a BeautifulSoup tag to Markdown text."""
    if isinstance(tag, Comment):
        return ""

    if isinstance(tag, NavigableString):
        text = str(tag)
        # Preserve whitespace inside <pre>
        parent = tag.parent
        while parent:
            if parent.name == "pre":
                return text
            parent = parent.parent
        # Collapse whitespace for normal text
        text = re.sub(r"[ \t]+", " ", text)
        # Don't strip leading/trailing space entirely – the caller handles spacing
        return text

    if not isinstance(tag, Tag):
        return ""

    name = tag.name

    # ------------------------------------------------------------------
    # Block elements
    # ------------------------------------------------------------------

    # Headings
    if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
        level = int(name[1])
        inner = _convert_children_inline(tag).strip()
        if not inner:
            return ""
        prefix = "#" * level
        return f"\n\n{prefix} {inner}\n\n"

    # Paragraphs
    if name == "p":
        inner = _convert_children_inline(tag).strip()
        if not inner:
            return ""
        return f"\n\n{inner}\n\n"

    # Code blocks: <pre> containing <code>
    if name == "pre":
        code_tag = tag.find("code")
        if code_tag:
            lang = _get_language_from_class(code_tag) or _get_language_from_class(tag)
            code_text = code_tag.get_text()
        else:
            lang = _get_language_from_class(tag)
            code_text = tag.get_text()
        # Remove one trailing newline if present
        if code_text.endswith("\n"):
            code_text = code_text[:-1]
        return f"\n\n```{lang}\n{code_text}\n```\n\n"

    # Blockquotes
    if name == "blockquote":
        inner = _convert_children(tag).strip()
        lines = inner.split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        return f"\n\n{quoted}\n\n"

    # Horizontal rules
    if name == "hr":
        return "\n\n---\n\n"

    # Unordered lists
    if name == "ul":
        return _convert_list(tag, ordered=False, depth=list_depth)

    # Ordered lists
    if name == "ol":
        return _convert_list(tag, ordered=True, depth=list_depth)

    # Tables
    if name == "table":
        return _convert_table(tag)

    # Definition lists
    if name == "dl":
        return _convert_definition_list(tag)

    # Images (block-level when direct child of a block container)
    if name == "img":
        return _convert_image(tag)

    # <br>
    if name == "br":
        return "\n"

    # <div>, <section>, <aside> – just process children with spacing
    if name in ("div", "section", "aside", "main", "article", "figure", "figcaption", "details", "summary"):
        inner = _convert_children(tag)
        return f"\n{inner}\n"

    # ------------------------------------------------------------------
    # Inline elements – delegate to inline converter
    # ------------------------------------------------------------------
    if name in INLINE_TAGS:
        return _convert_inline_tag(tag)

    # Default: process children
    return _convert_children(tag)


def _convert_inline_tag(tag: Tag) -> str:
    """Convert an inline-level tag to Markdown."""
    name = tag.name
    inner = _convert_children_inline(tag)

    if name in ("b", "strong"):
        stripped = inner.strip()
        if not stripped:
            return ""
        # Preserve surrounding whitespace
        lead = " " if inner and inner[0] == " " else ""
        trail = " " if inner and inner[-1] == " " else ""
        return f"{lead}**{stripped}**{trail}"

    if name in ("i", "em"):
        stripped = inner.strip()
        if not stripped:
            return ""
        lead = " " if inner and inner[0] == " " else ""
        trail = " " if inner and inner[-1] == " " else ""
        return f"{lead}*{stripped}*{trail}"

    if name in ("del", "s", "strike"):
        stripped = inner.strip()
        if not stripped:
            return ""
        return f"~~{stripped}~~"

    if name == "code":
        # Inline code – do not recurse, just get text
        text = tag.get_text()
        if "`" in text:
            return f"`` {text} ``"
        return f"`{text}`"

    if name == "kbd":
        text = tag.get_text()
        return f"`{text}`"

    if name == "a":
        href = tag.get("href", "")
        if not href or href.startswith("#") or href.startswith("javascript:"):
            # Skip empty/anchor-only/javascript links, just return text
            return inner
        text = inner.strip()
        if not text:
            return ""
        return f"[{text}]({href})"

    if name == "img":
        return _convert_image(tag)

    if name == "mark":
        stripped = inner.strip()
        if not stripped:
            return ""
        return f"=={stripped}=="

    if name in ("sub", "sup", "u", "abbr", "var", "small", "span"):
        return inner

    return inner


def _convert_image(tag: Tag) -> str:
    """Convert an <img> tag to Markdown."""
    src = tag.get("src", "")
    if not src:
        return ""
    alt = tag.get("alt", "").strip()
    title = tag.get("title", "").strip()
    if title:
        return f'![{alt}]({src} "{title}")'
    return f"![{alt}]({src})"


def _convert_children(tag: Tag) -> str:
    """Convert all children of a tag, producing block-level output."""
    parts = []
    for child in tag.children:
        parts.append(_convert_tag(child))
    return "".join(parts)


def _convert_children_inline(tag: Tag) -> str:
    """Convert all children of a tag, producing inline-level output."""
    parts = []
    for child in tag.children:
        if isinstance(child, NavigableString):
            if isinstance(child, Comment):
                continue
            text = str(child)
            # Collapse whitespace
            parent = child.parent
            in_pre = False
            while parent:
                if parent.name == "pre":
                    in_pre = True
                    break
                parent = parent.parent
            if not in_pre:
                text = re.sub(r"[ \t]+", " ", text)
            parts.append(text)
        elif isinstance(child, Tag):
            if child.name in INLINE_TAGS or child.name == "img":
                parts.append(_convert_inline_tag(child) if child.name != "img" else _convert_image(child))
            elif child.name == "br":
                parts.append("\n")
            elif child.name in ("code",):
                parts.append(_convert_inline_tag(child))
            else:
                # Block inside inline context – just get its inline rendering
                parts.append(_convert_children_inline(child))
    return "".join(parts)


# ---------------------------------------------------------------------------
# Lists
# ---------------------------------------------------------------------------

def _convert_list(tag: Tag, ordered: bool, depth: int) -> str:
    """Convert <ul> or <ol> to Markdown list."""
    items = []
    counter = int(tag.get("start", 1)) if ordered else 0
    indent = "    " * depth

    for child in tag.children:
        if isinstance(child, NavigableString):
            continue
        if not isinstance(child, Tag):
            continue
        if child.name != "li":
            continue

        # Separate nested lists from inline content
        nested_parts = []
        inline_parts = []
        for sub in child.children:
            if isinstance(sub, Tag) and sub.name in ("ul", "ol"):
                nested_parts.append(sub)
            else:
                inline_parts.append(sub)

        # Build inline text for this item
        inline_text_parts = []
        for part in inline_parts:
            inline_text_parts.append(_convert_tag(part, list_depth=depth + 1))
        inline_text = "".join(inline_text_parts).strip()
        # Collapse internal newlines in the item text (but not from nested lists)
        inline_text = re.sub(r"\n{2,}", "\n", inline_text)

        if ordered:
            prefix = f"{indent}{counter}. "
            counter += 1
        else:
            prefix = f"{indent}- "

        item_lines = inline_text.split("\n")
        first_line = f"{prefix}{item_lines[0]}"
        continuation_indent = " " * len(prefix)
        rest_lines = [f"{continuation_indent}{line}" for line in item_lines[1:] if line.strip()]
        full_item = "\n".join([first_line] + rest_lines)
        items.append(full_item)

        # Process nested lists
        for nested in nested_parts:
            is_ordered = nested.name == "ol"
            nested_md = _convert_list(nested, ordered=is_ordered, depth=depth + 1)
            items.append(nested_md.strip("\n"))

    result = "\n".join(items)
    return f"\n\n{result}\n\n" if depth == 0 else f"\n{result}\n"


# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

def _convert_table(tag: Tag) -> str:
    """Convert an HTML table to a Markdown table."""
    rows = []
    alignments = []

    # Gather all rows from thead, tbody, tfoot, or direct children
    for section in (tag.find("thead"), tag.find("tbody"), tag.find("tfoot")):
        if section:
            for tr in section.find_all("tr", recursive=False):
                rows.append(tr)

    # If no thead/tbody structure, get direct tr children
    if not rows:
        rows = tag.find_all("tr", recursive=False)
        # Also check one level deep (table > tbody implicit)
        if not rows:
            rows = tag.find_all("tr")

    if not rows:
        return ""

    # Parse cells
    table_data = []
    for tr in rows:
        cells = tr.find_all(["th", "td"], recursive=False)
        row_data = []
        for cell in cells:
            text = _convert_children_inline(cell).strip()
            text = text.replace("|", "\\|").replace("\n", " ")
            row_data.append(text)
        table_data.append(row_data)

    if not table_data:
        return ""

    # Determine column count
    max_cols = max(len(row) for row in table_data)

    # Pad rows to same length
    for row in table_data:
        while len(row) < max_cols:
            row.append("")

    # Detect alignment from first row's <th>/<td> style or align attribute
    first_tr = rows[0] if rows else None
    if first_tr:
        cells = first_tr.find_all(["th", "td"], recursive=False)
        for cell in cells:
            align = (cell.get("align") or "").lower()
            if not align:
                style = (cell.get("style") or "").lower()
                m = re.search(r"text-align:\s*(left|center|right)", style)
                if m:
                    align = m.group(1)
            alignments.append(align)

    while len(alignments) < max_cols:
        alignments.append("")

    # Column widths
    col_widths = [3] * max_cols  # minimum width 3 for separator
    for row in table_data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(cell))

    # Build header
    header_row = table_data[0]
    header_line = "| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(header_row)) + " |"

    # Build separator
    sep_parts = []
    for i in range(max_cols):
        width = col_widths[i]
        align = alignments[i] if i < len(alignments) else ""
        if align == "center":
            sep_parts.append(":" + "-" * (width - 2) + ":" if width > 2 else ":-:")
        elif align == "right":
            sep_parts.append("-" * (width - 1) + ":")
        elif align == "left":
            sep_parts.append(":" + "-" * (width - 1))
        else:
            sep_parts.append("-" * width)
    sep_line = "| " + " | ".join(sep_parts) + " |"

    # Build body rows
    body_lines = []
    for row in table_data[1:]:
        line = "| " + " | ".join(cell.ljust(col_widths[i]) for i, cell in enumerate(row)) + " |"
        body_lines.append(line)

    parts = [header_line, sep_line] + body_lines
    table_md = "\n".join(parts)
    return f"\n\n{table_md}\n\n"


# ---------------------------------------------------------------------------
# Definition lists
# ---------------------------------------------------------------------------

def _convert_definition_list(tag: Tag) -> str:
    """Convert <dl> to Markdown-style definition list."""
    parts = []
    for child in tag.children:
        if not isinstance(child, Tag):
            continue
        if child.name == "dt":
            text = _convert_children_inline(child).strip()
            if text:
                parts.append(f"\n**{text}**")
        elif child.name == "dd":
            text = _convert_children_inline(child).strip()
            if text:
                parts.append(f": {text}")

    return "\n\n" + "\n".join(parts) + "\n\n" if parts else ""


# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------

def _post_process(text: str) -> str:
    """Clean up the generated Markdown."""
    # Strip trailing whitespace on each line
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    # Collapse 3+ consecutive blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip leading/trailing whitespace from entire document
    text = text.strip()
    # Ensure file ends with a single newline
    text += "\n"
    return text


# ---------------------------------------------------------------------------
# Frontmatter
# ---------------------------------------------------------------------------

def _build_frontmatter(metadata: dict) -> str:
    """Build YAML frontmatter string."""
    lines = ["---"]
    if metadata.get("title"):
        # Escape YAML special chars in title
        title = metadata["title"].replace('"', '\\"')
        lines.append(f'title: "{title}"')
    if metadata.get("description"):
        desc = metadata["description"].replace('"', '\\"')
        lines.append(f'description: "{desc}"')
    if metadata.get("url"):
        lines.append(f'source: "{metadata["url"]}"')
    if metadata.get("language"):
        lines.append(f'language: "{metadata["language"]}"')
    lines.append(f'scraped_at: "{datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}"')
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main conversion function
# ---------------------------------------------------------------------------

def convert_html_to_markdown(
    html: str,
    url: str = None,
    include_frontmatter: bool = True,
    content_selector: str = None,
) -> str:
    """Convert HTML content to clean Markdown.

    Args:
        html: Raw HTML string (or bytes).
        url: Source URL for metadata/frontmatter.
        include_frontmatter: Whether to prepend YAML frontmatter.
        content_selector: Optional CSS selector to locate main content area.

    Returns:
        Markdown string.
    """
    # Handle bytes input
    if isinstance(html, bytes):
        html = decode_html(html)

    # Parse
    soup = _get_parser(html)

    # Extract metadata before cleaning (some meta tags may be in <head>)
    metadata = extract_metadata(soup, url)

    # Clean unwanted elements
    _clean_html(soup)

    # Find main content
    content = _find_main_content(soup, content_selector)

    # Convert to markdown
    raw_md = _convert_tag(content)

    # Post-process
    md = _post_process(raw_md)

    # Add frontmatter
    if include_frontmatter:
        frontmatter = _build_frontmatter(metadata)
        md = frontmatter + "\n\n" + md

    return md


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert HTML to Markdown using BeautifulSoup4."
    )
    parser.add_argument(
        "--url",
        default=None,
        help="Source URL (included in frontmatter metadata).",
    )
    parser.add_argument(
        "--no-frontmatter",
        action="store_true",
        help="Omit YAML frontmatter from output.",
    )
    parser.add_argument(
        "--selector",
        default=None,
        help="CSS selector for main content area (e.g. '.docs-content').",
    )
    parser.add_argument(
        "infile",
        nargs="?",
        type=argparse.FileType("r", encoding="utf-8"),
        default=sys.stdin,
        help="Input HTML file (defaults to stdin).",
    )
    args = parser.parse_args()

    html = args.infile.read()
    md = convert_html_to_markdown(
        html,
        url=args.url,
        include_frontmatter=not args.no_frontmatter,
        content_selector=args.selector,
    )
    sys.stdout.write(md)


if __name__ == "__main__":
    main()
