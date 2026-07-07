---
name: web-scraper
description: Scrape websites, documentation sites, and single pages to clean Markdown
triggers:
  - scrape
  - scraping
  - web scraper
  - crawl site
  - crawl website
  - scrape documentation
  - scrape docs
  - scrape page
  - scrape url
  - extract content from website
  - download documentation
  - convert website to markdown
  - website to markdown
---

# Web Scraper Skill

Scrape web pages, crawl entire sites, and extract documentation into clean Markdown files.

## Quick Decision Tree

```
User wants to scrape something
├── Single page? → scrape_page.py
├── Entire site (generic)? → crawl_site.py
└── Documentation site? → scrape_docs.py (auto-detects framework)
```

## Scripts Location

All scripts are in `~/.claude/skills/web-scraper/scripts/`.

## 1. Scrape a Single Page

**When to use:** User wants content from one specific URL.

```bash
python3 ~/.claude/skills/web-scraper/scripts/scrape_page.py "<url>" -o output.md
```

Options:
| Flag | Description |
|------|-------------|
| `-o FILE` | Output file (default: stdout) |
| `-s SELECTOR` | CSS selector for content area (e.g. `.docs-content`) |
| `-j, --javascript` | Force JavaScript rendering via Playwright |
| `--wait-for SEL` | Wait for CSS selector before capturing (implies -j) |
| `--timeout N` | Request timeout in seconds (default: 30) |
| `--no-robots` | Skip robots.txt check |
| `--no-frontmatter` | Omit YAML frontmatter from output |
| `--retries N` | Number of retry attempts (default: 3) |

**Examples:**
```bash
# Simple static page
python3 ~/.claude/skills/web-scraper/scripts/scrape_page.py "https://example.com/blog/post" -o post.md

# JavaScript-rendered SPA
python3 ~/.claude/skills/web-scraper/scripts/scrape_page.py "https://app.example.com/docs" -j --wait-for ".content" -o docs.md

# Extract only specific section
python3 ~/.claude/skills/web-scraper/scripts/scrape_page.py "https://docs.site.com/api" -s ".api-reference" -o api.md
```

## 2. Crawl an Entire Site

**When to use:** User wants to scrape multiple pages from a site (not specifically documentation).

```bash
python3 ~/.claude/skills/web-scraper/scripts/crawl_site.py "<start_url>" -o ./output_dir
```

Options:
| Flag | Description |
|------|-------------|
| `-o DIR` | Output directory (default: `./scraped`) |
| `-d N` | Max crawl depth (default: 3) |
| `-m N` | Max pages to scrape (default: 100) |
| `--delay N` | Delay between requests in seconds (default: 1.0) |
| `-p PATTERN` | Regex pattern to filter URLs |
| `-s SELECTOR` | CSS selector for content area |
| `-j, --javascript` | Use JavaScript rendering |
| `--no-robots` | Skip robots.txt check |
| `--resume` | Continue a previously interrupted crawl |
| `--retries N` | Number of retry attempts (default: 3) |

**Examples:**
```bash
# Crawl a blog (max 50 pages, depth 2)
python3 ~/.claude/skills/web-scraper/scripts/crawl_site.py "https://blog.example.com" -o ./blog -d 2 -m 50

# Crawl only /api/ pages
python3 ~/.claude/skills/web-scraper/scripts/crawl_site.py "https://docs.example.com/api" -o ./api-docs -p "/api/"

# Resume interrupted crawl
python3 ~/.claude/skills/web-scraper/scripts/crawl_site.py "https://docs.example.com" -o ./docs --resume
```

**Output:**
```
output_dir/
├── INDEX.md        # Table of contents with links
├── index.json      # Metadata for resume functionality
├── page1.md
├── page2.md
└── ...
```

## 3. Scrape Documentation Sites

**When to use:** User wants to scrape a documentation site. This is the smartest option — it auto-detects the documentation framework and extracts pages in logical order from the sidebar navigation.

```bash
python3 ~/.claude/skills/web-scraper/scripts/scrape_docs.py "<docs_url>" -o ./output_dir
```

Options:
| Flag | Description |
|------|-------------|
| `-o DIR` | Output directory (default: `./scraped_docs`) |
| `-m N` | Max pages (default: 200) |
| `-j, --javascript` | Force JavaScript rendering |
| `-c, --consolidate` | Generate single FULL_DOCS.md with all content |
| `-s SELECTOR` | Override content CSS selector |
| `--delay N` | Delay between requests (default: 1.0) |
| `--no-robots` | Skip robots.txt check |
| `--resume` | Continue interrupted scrape |
| `--retries N` | Retry attempts (default: 3) |

**Supported frameworks (auto-detected):**
- Docusaurus (v2/v3)
- GitBook
- ReadTheDocs / Sphinx
- MkDocs (Material theme)
- Next.js documentation sites
- Mintlify
- VuePress
- Generic (fallback)

**Examples:**
```bash
# Scrape ElevenLabs docs with consolidated output
python3 ~/.claude/skills/web-scraper/scripts/scrape_docs.py "https://elevenlabs.io/docs/agents-platform" -o ./elevenlabs-docs -j -c

# Scrape Docusaurus docs
python3 ~/.claude/skills/web-scraper/scripts/scrape_docs.py "https://docusaurus.io/docs" -o ./docusaurus-docs -c

# Scrape ReadTheDocs project
python3 ~/.claude/skills/web-scraper/scripts/scrape_docs.py "https://requests.readthedocs.io/en/latest/" -o ./requests-docs -c
```

**Output:**
```
output_dir/
├── INDEX.md           # Ordered table of contents
├── index.json         # Metadata
├── FULL_DOCS.md       # Only with -c flag: all docs in one file
├── introduction.md
├── getting-started.md
├── api_overview.md
└── ...
```

## Typical Workflow

### Scrape docs → Analyze → Generate guide

```bash
# Step 1: Scrape the documentation
python3 ~/.claude/skills/web-scraper/scripts/scrape_docs.py "https://elevenlabs.io/docs/agents-platform" -o ./elevenlabs -j -c

# Step 2: Read the consolidated doc
# Claude reads ./elevenlabs/FULL_DOCS.md

# Step 3: Analyze and generate a guide based on the scraped content
```

### Scrape a single reference page

```bash
# Scrape one API reference page
python3 ~/.claude/skills/web-scraper/scripts/scrape_page.py "https://api.example.com/reference/endpoints" -s ".api-content" -o api-reference.md

# Claude reads api-reference.md and works with it
```

## JavaScript Rendering

Some sites (SPAs, React apps) require JavaScript to render content. The scripts auto-detect this, but you can force it:

```bash
# Auto-detect (default behavior)
python3 ~/.claude/skills/web-scraper/scripts/scrape_page.py "https://spa-site.com"

# Force JS rendering
python3 ~/.claude/skills/web-scraper/scripts/scrape_page.py "https://spa-site.com" -j

# Wait for specific element
python3 ~/.claude/skills/web-scraper/scripts/scrape_page.py "https://spa-site.com" -j --wait-for ".main-content"
```

**Prerequisite for JS rendering:**
```bash
npx playwright install chromium
```

## Dependencies

Already installed (no action needed):
- Python 3.12+ with beautifulsoup4, requests, lxml, html5lib
- Node.js 20+ (for Playwright rendering)

Only needed for JavaScript-heavy sites:
```bash
npx playwright install chromium
```

## Error Handling

| Situation | Behavior |
|-----------|----------|
| robots.txt blocks URL | Warns user, skips page (use `--no-robots` to override) |
| HTTP 429 (rate limit) | Exponential backoff: 2s → 4s → 8s → 16s |
| Page requires JavaScript | Auto-detects and suggests using `-j` flag |
| Playwright not installed | Shows install command: `npx playwright install chromium` |
| Crawl interrupted | Use `--resume` to continue from where it stopped |
| Encoding issues | Auto-detects charset from headers and meta tags |

## 4. Scrape Authenticated / Login-Required Sites (e.g. Skool)

**When to use:** Site blocks headless browsers or requires login (Skool, private communities, dashboards).

**Method:** Launch visible Chromium (non-headless) with `dangerouslyDisableSandbox: true`, let user login, save cookies, then reuse cookies for headless scraping.

### Step 1: Launch visible browser for user login

```python
# File: /tmp/claude-1000/auth_login.py
from playwright.sync_api import sync_playwright
import json, time

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=False,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled', '--disable-gpu']
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    )
    page = context.new_page()
    page.goto('https://www.skool.com/login', timeout=30000)
    page.wait_for_load_state('networkidle')
    print("Browser open - user has 120s to login")
    time.sleep(120)  # Wait for user to login

    cookies = context.cookies()
    with open('/tmp/claude-1000/site_cookies.json', 'w') as f:
        json.dump(cookies, f)
    print(f"Cookies saved: {len(cookies)}")
    browser.close()
```

**IMPORTANT:** Must run with `dangerouslyDisableSandbox: true` and `run_in_background: true`.

### Step 2: Reuse cookies for headless scraping

```python
# File: /tmp/claude-1000/auth_scrape.py
from playwright.sync_api import sync_playwright
import json

with open('/tmp/claude-1000/site_cookies.json', 'r') as f:
    cookies = json.load(f)

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-blink-features=AutomationControlled']
    )
    context = browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    )
    context.add_cookies(cookies)
    page = context.new_page()

    page.goto('https://TARGET_URL', timeout=30000)
    page.wait_for_load_state('networkidle')
    page.wait_for_timeout(3000)

    # Screenshot
    page.screenshot(path='/tmp/claude-1000/output.png', full_page=True)

    # Text content
    content = page.inner_text('body')
    with open('/tmp/claude-1000/output.txt', 'w') as f:
        f.write(content)

    # Extract links
    links = page.eval_on_selector_all('a[href]',
        'els => els.map(e => ({text: e.innerText.trim().substring(0,100), href: e.href}))')

    browser.close()
```

**Also runs with `dangerouslyDisableSandbox: true`** (headless Playwright also needs it for Skool).

### Tested sites
- **Skool** (www.skool.com) - Requires this method. Blocks all headless/anonymous access.

### Cookie persistence
Cookies are saved at `/tmp/claude-1000/site_cookies.json`. They persist within the session. For multi-page scraping, reuse the same cookie file without re-login.

## References

- `references/selectors-guide.md` — CSS selectors for common documentation frameworks
