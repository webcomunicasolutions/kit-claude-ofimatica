# LLMWhisperer Modes & Features

## Table of Contents
- [Processing Modes](#processing-modes)
- [Output Modes](#output-modes)
- [File Formats Supported](#file-formats-supported)
- [Languages](#languages)
- [Webhooks](#webhooks)
- [Highlighting](#highlighting)

---

## Processing Modes

### Feature Matrix

| Feature | native_text | low_cost | high_quality | form | table |
|---------|-------------|----------|--------------|------|-------|
| PDF (not scanned) | Yes | Yes | Yes | Yes | Yes |
| PDF (scanned) | No | Yes | Yes | Yes | Yes |
| PDF (with forms) | No | No | No | Yes | Yes |
| Images | No | Yes | Yes | Yes | Yes |
| MS Office (Word/PPT) | No | Yes | Yes | Yes | Yes |
| MS Office Excel | No | No | No | Yes | No |
| LibreOffice (all) | No | Yes | Yes | Yes | Yes |
| Checkbox/Radio detection | No | No | No | Yes | Yes |
| Lines reproduction | No | Yes | Yes | Yes | Yes |
| Speed | Very fast | Medium | Fast | Fast | Fast |
| Image preprocessing | No | Yes | No | No | No |
| Languages | All unicode | 120+ | 300+ | 300+ | 300+ |
| Handwriting | No | Basic | Yes | Yes | Yes |
| Layout preserving | Yes | Yes | Yes | Yes | Yes |
| AI/ML enhancement | No | No | Yes | Yes | Yes |
| Rotation/skew fix | N/A | No | Yes | Yes | Yes |
| Auto repair PDFs | Yes | Yes | Yes | Yes | Yes |

### Mode Selection Guide

| Scenario | Recommended Mode |
|----------|-----------------|
| Low latency, native PDFs, cost-sensitive | `native_text` |
| High quality scanned docs, no handwriting | `low_cost` |
| Low quality scans, handwritten docs | `high_quality` |
| Checkboxes, radio buttons, form fields | `form` |
| Financial statements, invoices, tables | `table` |

### API Parameter

```
mode=native_text | low_cost | high_quality | form | table
```

Default: `form`

---

## Output Modes

| Mode | Description |
|------|-------------|
| `layout_preserving` | Maintains document structure, removes whitespace, optimized for LLM token consumption |
| `text` | Raw text extraction without layout processing. Fallback for docs with many fonts/sizes |

---

## File Formats Supported

### Word Processing
DOCX, DOC, ODT

### Presentations
PPTX, PPT, ODP

### Spreadsheets
XLSX, XLS, ODS

### Documents & Text
PDF, TXT, CSV, JSON, TSV, XML, HTML

### Images
BMP, GIF, JPEG, JPG, PNG, TIF, TIFF, WEBP

---

## Languages

- **native_text / low_cost**: English-focused, limited multilingual
- **high_quality / form / table**: 300+ printed languages, 12 handwritten languages

### Handwritten Languages (form, table, high_quality modes)
English, Chinese Simplified, French, German, Italian, Japanese, Korean, Portuguese, Spanish, Russian, Thai, Arabic

For full language list with codes, see https://docs.unstract.com/llmwhisperer/llm_whisperer/languages_supported/

---

## Webhooks

Register webhooks to receive results automatically instead of polling.

### Setup
1. Register via `POST /whisper-manage-callback` with `url`, `auth_token`, `webhook_name`
2. Pass `use_webhook=<name>` in `/whisper` requests
3. LLMWhisperer calls your URL with extracted text on completion

### Requirements
- Publicly accessible URL accepting POST
- Bearer token auth only (pass token without "Bearer" prefix, empty string if no auth)
- Must return 200 to acknowledge
- Max 3 retries on failure

### Webhook Payload
```json
{
  "payload_status": {"status": "success", "message": "", "whisper_hash": ""},
  "line_metadata": [],
  "confidence_metadata": [],
  "result_text": "extracted_text",
  "metadata": {}
}
```

---

## Highlighting

Enable source document highlighting for review UIs.

### How It Works
1. Call `/whisper` with `add_line_nos=true` - adds hex line numbers to output
2. Prompt LLM to include line numbers in extraction results
3. Call `/highlights` API with line numbers to get bounding box coordinates
4. Use coordinates to highlight in your UI

### Python Helper
```python
page, x1, y1, x2, y2 = client.get_highlight_rect(
    line_metadata=result["extraction"]["line_metadata"][line_no],
    line_no=line_no,
    target_width=2480,
    target_height=3508
)
```

### Bounding Box Format
Full page width highlighting. Coordinates: `[page_no, base_y, height, page_height]`
- x1 = 0, x2 = page_width (always full width)
- y ranges from base_y-height to base_y
