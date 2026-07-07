# LLMWhisperer Editions & Deployment

## Table of Contents
- [Cloud Edition](#cloud-edition)
- [On-Prem Edition](#on-prem-edition)
- [Pricing](#pricing)
- [FAQs - Migration v1 to v2](#migration-v1-to-v2)

---

## Cloud Edition

Fully managed SaaS. Sign up, get API key, start extracting.

### Regions

| Region | Base URL |
|--------|----------|
| US Central | `https://llmwhisperer-api.us-central.unstract.com/api/v2` |
| EU West | `https://llmwhisperer-api.eu-west.unstract.com/api/v2` |

### Key Features
- Layout-preserving text extraction
- Checkbox and radio button detection
- Auto-compaction to reduce LLM tokens
- Image preprocessing (Gaussian Blur, Median Filtering, Contrast)
- 300+ language support with handwriting recognition
- Auto mode switching (native text to OCR)
- Auto PDF repair
- Supports PDFs, images, MS Office, LibreOffice

### Getting Started
1. Register at https://unstract.com/llmwhisperer/
2. Try the Playground
3. Integrate via API, Python client, JS client, or n8n node

---

## On-Prem Edition

Deployed in your infrastructure (AWS, Azure, GCP) via Kubernetes Helm chart.

### Key Features
- Same features as Cloud Edition
- Data stays within your VPC
- Kubernetes-native (Helm charts)
- Configurable node profiles
- GPU support for document insights mode
- Bundled dashboard for monitoring

### Infrastructure Prerequisites
- Kubernetes cluster
- PostgreSQL database
- DNS & SSL certificates
- Node profile configuration

### Deployment
Deployed via Helm chart. See https://docs.unstract.com/llmwhisperer/llm_whisperer/on_prem/on_prem_deployment/ for full guide.

---

## Pricing

- **Free plan**: 100 pages/day, no monthly quota
- **Paid plans**: Pay-as-you-go, no flat fee
  - Tiered: $1 to $15 per 1,000 pages depending on mode
  - Metered by pages processed per mode
  - No daily limit

Details: https://unstract.com/pricing/

---

## Migration v1 to v2

### Breaking Changes
- New base URL: `.../api/v2` (not `.../api/v1`)
- `whisper-hash` parameter renamed to `whisper_hash`
- No sync mode - all requests are async (use `wait_for_completion` in clients)
- `processing_mode` and `ocr_provider` replaced by `mode`
- `force_text_processing` removed
- Python client: `LLMWhispererClientV2` (not `LLMWhispererClient`)
- JS client: version 2.x.y required

### New in v2
- 5 processing modes (native_text, low_cost, high_quality, form, table)
- Webhook support
- `tag` and `file_name` for auditing
- `mark_vertical_lines` and `mark_horizontal_lines`
- `line_splitter_strategy` parameter
- Usage stats by tag

### Client Changes

**Python**: `pip install llmwhisperer-client>=2.0.0`
```python
# v1
from unstract.llmwhisperer.client import LLMWhispererClient
# v2
from unstract.llmwhisperer import LLMWhispererClientV2
```

**JavaScript**: `npm install llmwhisperer-client@^2.0.0`
