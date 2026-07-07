# LLMWhisperer v2 API Reference

## Table of Contents
- [Authentication](#authentication)
- [Extraction API - POST /whisper](#extraction-api)
- [Status API - GET /whisper-status](#status-api)
- [Retrieve API - GET /whisper-retrieve](#retrieve-api)
- [Detail API - GET /whisper-detail](#detail-api)
- [Highlight API - GET /highlights](#highlight-api)
- [Usage Metrics API - GET /get-usage-info](#usage-metrics-api)
- [Usage Stats API - GET /usage](#usage-stats-api)
- [Webhook Management API - /whisper-manage-callback](#webhook-management-api)

## Authentication

All APIs require `unstract-key` header with API key.

```
-H 'unstract-key: <YOUR_API_KEY>'
```

Base URLs:
- US: `https://llmwhisperer-api.us-central.unstract.com/api/v2`
- EU: `https://llmwhisperer-api.eu-west.unstract.com/api/v2`

---

## Extraction API

`POST /whisper`

Convert PDF/scanned/Office documents to LLM-ready text. All requests are async (returns `202`).

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| mode | string | `form` | Processing mode: `native_text`, `low_cost`, `high_quality`, `form`, `table` |
| output_mode | string | `layout_preserving` | `layout_preserving` or `text` |
| page_seperator | string | `<<<` | Page separator string |
| pages_to_extract | string | (all) | Pages to extract, e.g. `1-5,7,21-` |
| median_filter_size | int | `0` | Noise removal filter (low_cost mode only) |
| gaussian_blur_radius | int | `0` | Blur radius for noise (low_cost mode only) |
| line_splitter_tolerance | float | `0.4` | Factor for line splitting (% of avg char height) |
| line_splitter_strategy | string | `left-priority` | Line splitting strategy |
| horizontal_stretch_factor | float | `1.0` | Horizontal stretch (use >1.0 for merged columns) |
| url_in_post | bool | `false` | If true, POST body contains URL instead of file |
| mark_vertical_lines | bool | `false` | Reproduce vertical lines (not for native_text) |
| mark_horizontal_lines | bool | `false` | Reproduce horizontal lines (requires mark_vertical_lines) |
| lang | string | `eng` | Language hint (currently auto-detected, ignored) |
| tag | string | `default` | Auditing tag for usage reports |
| file_name | string | | File name for auditing |
| use_webhook | string | | Registered webhook name to call on completion |
| webhook_metadata | string | | Metadata sent verbatim to webhook |
| add_line_nos | bool | `false` | Add line numbers for highlighting API |
| allow_rotated_text | bool | `true` | Include rotated/angled text in output |

### Request Body

Binary file data as `application/octet-stream`. Or URL as `text/plain` if `url_in_post=true`.

### Response (202)

```json
{
  "message": "Whisper Job Accepted",
  "status": "processing",
  "whisper_hash": "xxxxxa96|xxxxxxxxxxxxxxxxxxx4ed3da759ef670f"
}
```

### Curl Examples

```bash
# Upload file
curl -X POST 'https://llmwhisperer-api.us-central.unstract.com/api/v2/whisper?mode=form&output_mode=layout_preserving' \
  -H 'unstract-key: <KEY>' \
  --data-binary '@document.pdf'

# Process from URL
curl -X POST 'https://llmwhisperer-api.us-central.unstract.com/api/v2/whisper?mode=form&url_in_post=true' \
  -H 'unstract-key: <KEY>' \
  --data 'https://example.com/document.pdf'
```

---

## Status API

`GET /whisper-status`

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| whisper_hash | string | Yes | Hash from /whisper response |

### Possible Statuses (200)
- `accepted` - Added to processing queue
- `processing` - Still being processed
- `processed` - Ready to retrieve
- `error` - Failed (check message)
- `retrieved` - Already retrieved

### Response (200)
```json
{
  "status": "processed",
  "message": "",
  "detail": [
    { "page_no": 1, "message": "extraction_success", "execution_time_in_seconds": 4 }
  ]
}
```

---

## Retrieve API

`GET /whisper-retrieve`

**IMPORTANT: Text can only be retrieved ONCE** (security/privacy). Store the result.

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| whisper_hash | string | | Yes | Hash from /whisper |
| text_only | bool | false | No | If true, returns only text without metadata |

### Response (200, text_only=false)
```json
{
  "result_text": "extracted text...",
  "confidence_metadata": [],
  "metadata": {},
  "webhook_metadata": ""
}
```

**Confidence Metadata**: Per-line array of words with confidence < 0.9:
```json
[
  [],
  [{"confidence": "0.801", "text": "Please"}, {"confidence": "0.852", "text": "find"}]
]
```

### Errors
- 400: `"Whisper not ready : <status>"` or `"Whisper already delivered"`
- 404: `"Whisper job unknown"`

---

## Detail API

`GET /whisper-detail`

| Parameter | Type | Required |
|-----------|------|----------|
| whisper_hash | string | Yes |

### Response (200)
```json
{
  "whisper_hash": "<hash>",
  "mode": "form",
  "total_pages": 4,
  "requested_pages": 1,
  "processed_pages": 1,
  "processing_time_in_seconds": 120.88,
  "upload_file_size_in_kb": 618.488,
  "tag": "",
  "processing_started_at": "Mon, 10 Feb 2025 10:40:53 GMT",
  "completed_at": "Mon, 10 Feb 2025 10:40:58 GMT"
}
```

---

## Highlight API

`GET /highlights`

Requires `add_line_nos=true` in the original /whisper call.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| whisper_hash | string | Yes | Hash from /whisper |
| lines | string | Yes | Lines to retrieve, e.g. `1-5,7,21-` |

### Response (200)
```json
{
  "1": {
    "page": 0,
    "base_y": 155,
    "base_y_percent": 4.89,
    "height": 51,
    "height_percent": 1.61,
    "page_height": 3168,
    "raw": [0, 155, 51, 3168]
  }
}
```

Bounding box: full page width, y-coordinate is bottom of line.
```
(0, y-height) +-----------+ (page_width, y-height)
              |           |
(0, y)        +-----------+ (page_width, y)
```

---

## Usage Metrics API

`GET /get-usage-info` — No parameters.

### Response (Paid)
```json
{
  "subscription_plan": "<plan>",
  "monthly_quota": 10000,
  "current_page_count": 500,
  "current_page_count_native_text": 100,
  "current_page_count_low_cost": 200,
  "current_page_count_high_quality": 150,
  "current_page_count_form": 50,
  "daily_quota": -1,
  "overage_page_count": 0,
  "today_page_count": 25
}
```

### Response (Free)
```json
{
  "subscription_plan": "<plan>",
  "daily_quota": 100,
  "today_page_count": 25,
  "monthly_quota": -1,
  "current_page_count": -1,
  "overage_page_count": -1
}
```

---

## Usage Stats API

`GET /usage`

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| tag | string | | Yes | Filter by tag |
| from_date | string | | No | `YYYY-MM-DD` format |
| to_date | string | | No | `YYYY-MM-DD` format |

Default: last 30 days.

### Response (200)
```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "tag": "credit",
  "usage": [
    {"service_type": "form", "pages_processed": 150}
  ]
}
```

---

## Webhook Management API

`GET|POST|PUT|DELETE /whisper-manage-callback`

### Register (POST)
```bash
curl -X POST 'https://llmwhisperer-api.us-central.unstract.com/api/v2/whisper-manage-callback' \
  -H 'unstract-key: <KEY>' \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://your-endpoint.com/webhook","auth_token":"your-bearer-token","webhook_name":"my-webhook"}'
```

Registration sends a test payload to verify URL returns 200:
```json
{"payload_status":{"status":"test","message":"Testing webhook"},"result_text":"WEBHOOK_TEST"}
```

### Get Details (GET)
`?webhook_name=my-webhook`

### Update (PUT)
Same body as POST.

### Delete (DELETE)
`?webhook_name=my-webhook`

### Webhook Payload (delivered on completion)
```json
{
  "payload_status": {"status": "success", "message": "", "whisper_hash": ""},
  "line_metadata": [],
  "confidence_metadata": [],
  "result_text": "extracted_text",
  "metadata": {}
}
```

Webhook requirements:
- Publicly accessible URL accepting POST
- Bearer token auth only (pass token without "Bearer" prefix)
- Must return 200 to acknowledge
- Max 3 retries on failure
