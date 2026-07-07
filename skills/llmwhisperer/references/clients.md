# LLMWhisperer Clients & Integrations

## Table of Contents
- [Python Client](#python-client)
- [JavaScript Client](#javascript-client)
- [n8n Custom Node](#n8n-custom-node)
- [MCP Server](#mcp-server)

---

## Python Client

`pip install llmwhisperer-client` — Latest: **v2.7.0** (2026-03-16). Requires Python >=3.12.

### Version History (key changes)

| Version | Date | Change |
|---------|------|--------|
| 2.7.0 | 2026-03-16 | New `whisper_detail()` method |
| 2.6.0 | 2026-02-16 | Back-off retry with tenacity (auto-retry on 429/500+) |
| 2.5.0 | 2025-11-04 | New `include_line_confidence` parameter |
| 2.4.2 | 2025-07-21 | Fix TypeError when API returns JSON string |
| 2.4.1 | 2025-07-11 | Better error handling for non-JSON/empty responses |
| 2.4.0 | 2025-05-23 | Python version bump (>=3.12) |
| 2.3.0 | 2025-04-02 | Webhook management methods |
| 2.0.0 | 2024-11-05 | Initial v2 release |

### Import & Init

```python
from unstract.llmwhisperer import LLMWhispererClientV2
from unstract.llmwhisperer.client_v2 import LLMWhispererClientException

# Uses env vars LLMWHISPERER_API_KEY, LLMWHISPERER_BASE_URL_V2
client = LLMWhispererClientV2()

# Full constructor (v2.6.0+)
client = LLMWhispererClientV2(
    base_url="https://llmwhisperer-api.us-central.unstract.com/api/v2",
    api_key="your_key",
    logging_level="INFO",        # DEBUG, INFO, WARNING, ERROR
    custom_headers=None,         # dict merged with default headers (v2.6.0+)
    max_retries=3,               # retry on 429/500+ errors (v2.6.0+, 0=disable)
    retry_min_wait=1.0,          # min backoff seconds (v2.6.0+)
    retry_max_wait=60.0,         # max backoff seconds (v2.6.0+)
)
```

### Methods

**`whisper()`** - Process document

```python
result = client.whisper(
    file_path="doc.pdf",       # or stream=file_obj, or url="https://..."
    mode="form",               # native_text, low_cost, high_quality, form, table
    output_mode="layout_preserving",  # or "text"
    page_seperator="<<<",
    pages_to_extract="1-5,7",
    median_filter_size=0,      # low_cost mode only
    gaussian_blur_radius=0,    # low_cost mode only
    line_splitter_tolerance=0.4,
    horizontal_stretch_factor=1.0,
    mark_vertical_lines=False,
    mark_horizontal_lines=False,
    line_spitter_strategy="left-priority",  # NOTE: typo is official (spitter not splitter)
    add_line_nos=False,
    include_line_confidence=False,  # v2.5.0+ (requires add_line_nos=True)
    lang="eng",
    tag="default",
    filename="",
    use_webhook="",
    webhook_metadata="",
    wait_for_completion=False,  # True = sync mode (blocking)
    wait_timeout=180,          # seconds (for sync mode)
    encoding="utf-8",
)
```

**IMPORTANT**: `wait_for_completion` and `use_webhook` are mutually exclusive (raises exception).

**`whisper_status(whisper_hash)`** - Check status
```python
status = client.whisper_status(whisper_hash=result["whisper_hash"])
# status["status"]: "processing", "processed", "delivered", "unknown"
```

**`whisper_retrieve(whisper_hash)`** - Get result (ONE TIME ONLY)
```python
result = client.whisper_retrieve(whisper_hash="...")
# result["result_text"], result["confidence_metadata"]
```

**`whisper_detail(whisper_hash)`** - Get extraction metadata (v2.7.0+)
```python
detail = client.whisper_detail(whisper_hash="...")
# Returns: completed_at, mode, processed_pages, processing_started_at,
#          processing_time_in_seconds, requested_pages, tag, total_pages,
#          upload_file_size_in_kb, whisper_hash
```

**`get_usage_info()`** - Account usage
```python
usage = client.get_usage_info()
```

**`get_highlight_data(whisper_hash, lines, extract_all_lines=False)`** - Highlight data (v2.5.0+)
```python
data = client.get_highlight_data(
    whisper_hash="...",
    lines="1-5,7,21-",
    extract_all_lines=False  # True = return all lines
)
```

**`register_webhook(url, auth_token, webhook_name)`** - Register webhook (v2.3.0+)
```python
client.register_webhook("https://your-endpoint.com/hook", "bearer-token", "my-webhook")
```

**`get_webhook_details(webhook_name)`** - Get webhook config (v2.3.0+)
```python
details = client.get_webhook_details("my-webhook")
```

### Retry Behavior (v2.6.0+)

The client automatically retries on transient errors using tenacity:
- **Retryable**: HTTP 429 (rate limit), 500+ (server errors), connection errors, timeouts
- **Back-off**: exponential jitter (min 1s, max 60s by default)
- **Retry-After header**: honored when present (overrides backoff)
- **Deadline-aware**: respects `wait_timeout` budget
- **Disable**: set `max_retries=0` in constructor

### Async Polling Example

```python
import time
client = LLMWhispererClientV2()

result = client.whisper(file_path="document.pdf", mode="form")
if result["status_code"] == 202:
    while True:
        status = client.whisper_status(whisper_hash=result["whisper_hash"])
        if status["status"] == "processed":
            data = client.whisper_retrieve(whisper_hash=result["whisper_hash"])
            print(data["result_text"])
            break
        elif status["status"] in ("delivered", "unknown", "error"):
            break
        time.sleep(5)
```

### Sync Example

```python
result = client.whisper(
    file_path="document.pdf",
    mode="form",
    wait_for_completion=True,
    wait_timeout=200
)
print(result["extraction"]["result_text"])
```

### Error Handling

```python
try:
    result = client.whisper_retrieve("invalid_hash")
except LLMWhispererClientException as e:
    print(f"Error: {e.message}, Status: {e.status_code}")
```

### Result Format

Async (202):
```json
{"message": "Whisper Job Accepted", "status": "processing", "whisper_hash": "...", "status_code": 202, "extraction": {}}
```

Sync (200):
```json
{"message": "Whisper Job Accepted", "status": "processed", "whisper_hash": "...", "status_code": 200,
 "extraction": {"result_text": "...", "confidence_metadata": [], "line_metadata": [], "metadata": {}}}
```

---

## JavaScript Client

`npm install llmwhisperer-client` — Latest: **v2.5.0** (npm). Dependencies: axios, winston.

### Init

```javascript
const { LLMWhispererClientV2 } = require("llmwhisperer-client");

const client = new LLMWhispererClientV2({
    baseUrl: "https://llmwhisperer-api.us-central.unstract.com/api/v2",
    apiKey: "your_key",
    loggingLevel: "info"  // error, warn, info, debug
});
// Or use env vars: LLMWHISPERER_API_KEY, LLMWHISPERER_BASE_URL_V2
```

### Methods

```javascript
// Process document
const whisper = await client.whisper({
    filePath: "document.pdf",
    mode: "high_quality",
    outputMode: "layout_preserving",  // or "text"
    pagesToExtract: "1-2",
    lineSplitterTolerance: 0.4,
    horizontalStretchFactor: 1.0,
    markVerticalLines: false,
    markHorizontalLines: false,
    lineSplitterStrategy: "left-priority",
    addLineNos: false,
    waitForCompletion: true,  // sync mode
    waitTimeout: 120
});

// Async polling
const result = await client.whisper({ filePath: "doc.pdf" });
const status = await client.whisperStatus(result.whisper_hash);
const data = await client.whisperRetrieve(result.whisper_hash);

// Usage info
const usage = await client.getUsageInfo();

// Webhooks
await client.registerWebhook(webhookUrl, authToken, webhookName);
const details = await client.getWebhookDetails(webhookName);

// Highlighting
const rect = client.getHighlightRect(lineMetadata, targetWidth, targetHeight);
// Returns: { page, x1, y1, x2, y2 }
```

---

## n8n Custom Node

NPM package: `n8n-nodes-unstract`

### Installation
Install via n8n Community Nodes GUI installation.

### Credentials
Create LLMWhisperer credentials in n8n: enter "LLMWhisperer" when asked for app/service, provide API key.

### Input
- **File Contents**: Binary file from previous node
- All `/whisper` API parameters available as node fields

### Typical Workflow
1. Read Binary File node (or HTTP Request to download)
2. LLMWhisperer node (extracts text)
3. Process extracted text downstream

### Production Pattern: Two-Tier OCR (see spanish_invoices.md)
1. LLMWhisperer LOWCOST node (first attempt)
2. IF condition (check critical fields)
3. LLMWhisperer HIGH_Q node (fallback with tuned params)

---

## MCP Server

Docker image: `unstract/mcp-server`

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "extract_text": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/tmp:/tmp",
        "-e", "LLMWHISPERER_API_KEY",
        "unstract/mcp-server", "llm_whisperer"
      ],
      "env": {
        "LLMWHISPERER_API_KEY": "<your-key>"
      }
    }
  }
}
```

### Tool
`extract_text` - Submits file to LLMWhisperer API, polls for processing, retrieves extracted text. Supports all processing modes and output formats.

### Sample Prompt
"Extract text from the document /tmp/sample-bank_statement.pdf"
