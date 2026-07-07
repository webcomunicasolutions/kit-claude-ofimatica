---
name: llmwhisperer
description: "LLMWhisperer v2 OCR API by Unstract - extract text from PDFs, images, scanned documents, Office files for LLM consumption. Use when: (1) user mentions LLMWhisperer, Unstract, or whisper API, (2) needs OCR/text extraction from documents for LLMs, (3) works with LLMWhisperer Python/JS client, (4) configures LLMWhisperer in n8n workflows, (5) asks about document processing modes (native_text, low_cost, high_quality, form, table), (6) needs to integrate document extraction API into applications."
---

# LLMWhisperer v2 API

LLMWhisperer extracts text from complex documents (PDFs, images, Office files) in a layout-preserving format optimized for LLM consumption. All requests are async.

## Quick Reference

| Item | Value |
|------|-------|
| Base URL US | `https://llmwhisperer-api.us-central.unstract.com/api/v2` |
| Base URL EU | `https://llmwhisperer-api.eu-west.unstract.com/api/v2` |
| Auth Header | `unstract-key: <API_KEY>` |
| Python pkg | `pip install llmwhisperer-client` (v2.7.0, Python >=3.12) |
| JS pkg | `npm install llmwhisperer-client` (v2.5.0) |
| n8n node | `n8n-nodes-unstract` |
| Credentials | Store the API key in an env var or your local secrets vault (never hardcode) |

## Mode Selection Guide

| Your document | Use mode | Why |
|---------------|----------|-----|
| Digital PDF, need speed | `native_text` | Fastest, cheapest, text-layer only |
| Clean scan, budget-sensitive | `low_cost` | Basic OCR, no AI enhancement |
| Poor scan, handwriting | `high_quality` | AI/ML enhancement, rotation fix |
| Forms with checkboxes | `form` | Detects checkboxes, radio buttons |
| Invoices, financial tables | `table` | Preserves table structure |
| Spanish invoices (first pass) | `low_cost` | Fast + cheap, fallback to `high_quality` |
| Spanish invoices (fallback) | `high_quality` | With `tolerance=0.3`, `stretch=1.2` |
| Docs with visual semantics | Consider Gemini Vision | Checkmarks, spatial relationships |

## Processing Modes

| Mode | Scanned | Handwriting | Forms | Tables | Speed | AI/ML |
|------|---------|-------------|-------|--------|-------|-------|
| `native_text` | No | No | No | No | Very fast | No |
| `low_cost` | Yes | Basic | No | No | Medium | No |
| `high_quality` | Yes | Yes | No | No | Fast | Yes |
| `form` | Yes | Yes | Yes | No | Fast | Yes |
| `table` | Yes | Yes | No | Yes | Fast | Yes |

## API Workflow (Polling)

```
1. POST /whisper (file binary) -> 202 { whisper_hash }
2. GET  /whisper-status?whisper_hash=X -> { status: "processing"|"processed" }
3. GET  /whisper-retrieve?whisper_hash=X -> { result_text, confidence_metadata }
```

Alternative: register webhook via `/whisper-manage-callback`, pass `use_webhook=name` in `/whisper`.

**CRITICAL**: `/whisper-retrieve` only works ONCE per hash (security/privacy). Store the result immediately.

## Key Parameters

| Parameter | Default | Notes |
|-----------|---------|-------|
| `mode` | `form` | See mode selection guide above |
| `output_mode` | `layout_preserving` | `layout_preserving` or `text` |
| `line_splitter_tolerance` | `0.4` | Lower = conservative (0.3 for complex layouts) |
| `horizontal_stretch_factor` | `1.0` | >1.0 for narrow/compressed fonts (1.2 for Spanish invoices) |
| `mark_vertical_lines` | `false` | Reproduce table vertical lines in output |
| `mark_horizontal_lines` | `false` | Reproduce horizontal lines (requires vertical=true) |
| `pages_to_extract` | all | e.g. `1-5,7,21-` |
| `allow_rotated_text` | `true` | Include rotated/angled text in output |
| `url_in_post` | `false` | POST body contains URL instead of file |
| `include_line_confidence` | `false` | Line confidence in highlights (v2.5.0+, needs add_line_nos) |
| `add_line_nos` | `false` | Enable for highlighting API |
| `use_webhook` | | Registered webhook name |
| `tag` | `default` | For usage reports/auditing |

## Curl Example

```bash
curl -X POST 'https://llmwhisperer-api.us-central.unstract.com/api/v2/whisper?mode=form&output_mode=layout_preserving' \
  -H 'unstract-key: <KEY>' \
  --data-binary '@document.pdf'

curl 'https://llmwhisperer-api.us-central.unstract.com/api/v2/whisper-status?whisper_hash=HASH' \
  -H 'unstract-key: <KEY>'

curl 'https://llmwhisperer-api.us-central.unstract.com/api/v2/whisper-retrieve?whisper_hash=HASH' \
  -H 'unstract-key: <KEY>'
```

## Python Client Quick Start

```python
from unstract.llmwhisperer import LLMWhispererClientV2

client = LLMWhispererClientV2(
    base_url="https://llmwhisperer-api.us-central.unstract.com/api/v2",
    api_key="YOUR_KEY"
)

# Sync mode (waits for completion)
result = client.whisper(
    file_path="document.pdf",
    mode="form",
    wait_for_completion=True,
    wait_timeout=200
)
print(result["extraction"]["result_text"])

# Async mode
result = client.whisper(file_path="document.pdf", mode="high_quality")
# Poll with client.whisper_status(result["whisper_hash"])
# Retrieve with client.whisper_retrieve(result["whisper_hash"])
```

Env vars: `LLMWHISPERER_API_KEY`, `LLMWHISPERER_BASE_URL_V2`, `LLMWHISPERER_LOGGING_LEVEL`

**v2.6.0+**: Auto-retry on 429/500+ with exponential backoff (tenacity). Configure: `max_retries=3`, `retry_min_wait=1.0`, `retry_max_wait=60.0`.

**v2.7.0+**: `client.whisper_detail(whisper_hash)` returns extraction metadata (time, pages, size).

**NOTE**: `line_spitter_strategy` is the official param name (typo in upstream code, not `splitter`).

## n8n Integration Patterns

### Two-Tier OCR (production-proven for Spanish invoices)

```
PDF -> LLMWhisperer LOWCOST -> Gemini Extract -> Check fields
  |                                                    |
  |  if critical fields = "REVISAR" AND intentos_ocr=1 |
  |                                                    v
  +-------------- LLMWhisperer HIGH_Q <---------------+
                  (tolerance=0.3, stretch=1.2)
```

**LOWCOST node config:**
```json
{
  "host": "https://llmwhisperer-api.EU-west.unstract.com",
  "mode": "low_cost"
}
```

**HIGH_Q node config (fallback):**
```json
{
  "host": "https://llmwhisperer-api.EU-west.unstract.com",
  "mode": "high_quality",
  "line_splitter_tolerance": 0.3,
  "horizontal_stretch_factor": 1.2
}
```

**Fallback trigger condition** (n8n IF node):
```
intentos_ocr = 1 AND (
  fecha_expedicion = "REVISAR" OR
  nombre_empresa = "REVISAR" OR
  cif = "REVISAR" OR
  numero_factura = "REVISAR" OR
  total_factura = "REVISAR"
)
```

### Loop-Based Image Processing (for ZIP with multiple images)

```
ZIP -> IF EXISTS -> Decompress -> Loop (1 at a time) -> LLMWhisperer OCR
                                                              |
IF NOT EXISTS -> Empty Fallback                          (per image)
```

**Why loop instead of batch**: memory management, rate limit compliance, error isolation.

**Image OCR config:**
```json
{
  "host": "https://llmwhisperer-api.EU-west.unstract.com",
  "output_mode": "text",
  "mark_vertical_lines": true,
  "mark_horizontal_lines": true
}
```

### n8n Node Setup
1. Install `n8n-nodes-unstract` via Community Nodes
2. Create credential: type "LLMWhisperer", enter API key
3. Input: binary file from previous node (Download, HTTP Request, etc.)

## Troubleshooting & Lessons Learned

### Checkmark/symbol detection fails with OCR
**Problem**: Basic OCR converts checkmarks to random chars ("v", "/", "").
**Solution**: Use Gemini Vision for docs with visual semantics. LLMWhisperer excels at text/tables, not visual symbols.

### Table structure lost in output
**Problem**: Tables become plain text, column relationships disappear.
**Solution**: Enable `mark_vertical_lines=true` + `mark_horizontal_lines=true`. For structured data, use `mode=table`.

### Spanish invoices: complex layouts fail on low_cost
**Problem**: Merged cells, tight spacing, narrow fonts.
**Solution**: HIGH_Q with `line_splitter_tolerance=0.3` (conservative) + `horizontal_stretch_factor=1.2` (compensates narrow fonts).

### One-time retrieve gotcha
**Problem**: Called `/whisper-retrieve` twice, second call returns 400.
**Solution**: ALWAYS store result on first retrieve. Use duplicate detection (DB unique constraints, file renaming) to prevent re-submissions.

### n8n pairedItem breaks after Loop/Merge/Split
**Problem**: `$('NodeName').item.json.field` returns undefined after transformation nodes.
**Solution**: Use `$('NodeName').first().json.field` with try-catch fallback.

### Rate limits in high-volume scenarios
**Problem**: Batch processing triggers rate limits.
**Solution**: Process one at a time in loop, add delays between operations. Monitor with `/get-usage-info`.

### When to use LLMWhisperer vs Gemini Vision

| Criteria | LLMWhisperer | Gemini Vision |
|----------|-------------|---------------|
| Text extraction | Excellent | Good |
| Table structure | Good (with params) | Good (visual) |
| Checkmarks/symbols | Poor | Excellent |
| Speed | 5-20s | 3-5s |
| Cost per page | $0.01-0.015 | ~$0.002 |
| Batch volume | Rate limited | Quota limited |
| Best for | PDFs, text, tables | Images, forms, visual docs |

**Hybrid pattern**: LLMWhisperer for PDFs with text/tables + Gemini Vision for images with visual semantics.

## Reference Files

For detailed information, read these files as needed:

- **[API Reference](references/api_reference.md)** - All endpoints, parameters, request/response formats, error codes
- **[Clients & Integrations](references/clients.md)** - Python client API, JS client API, n8n node setup, MCP server
- **[Modes & Features](references/modes_features.md)** - Detailed mode comparison, file formats, languages, webhooks, highlighting
- **[Editions & Deployment](references/editions.md)** - Cloud vs On-Prem, pricing, deployment guide
- **[Spanish Invoice Patterns](references/spanish_invoices.md)** - Parameters, field extraction, tax rules, production patterns

Source docs: https://docs.unstract.com/llmwhisperer/
