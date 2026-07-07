# LLMWhisperer - Spanish Invoice Patterns

Production-proven patterns for processing Spanish invoices with LLMWhisperer.

## Two-Tier OCR Strategy

### Tier 1: LOWCOST (first pass, all invoices)

```json
{
  "host": "https://llmwhisperer-api.EU-west.unstract.com",
  "mode": "low_cost"
}
```

- Fast, cheap (~$0.01/page)
- Works for 80%+ of clean Spanish invoices
- Sets `intentos_ocr = 1`

### Tier 2: HIGH_Q (fallback, only when needed)

```json
{
  "host": "https://llmwhisperer-api.EU-west.unstract.com",
  "mode": "high_quality",
  "line_splitter_tolerance": 0.3,
  "horizontal_stretch_factor": 1.2
}
```

- `tolerance=0.3` (not default 0.5): prevents over-splitting complex Spanish layouts
- `stretch=1.2`: compensates for narrow/compressed fonts common in Spanish invoices
- Sets `intentos_ocr = 2`

### Fallback Trigger

HIGH_Q triggers when ANY critical field = "REVISAR" after LOWCOST extraction:
- `fecha_expedicion`
- `nombre_empresa`
- `cif`
- `numero_factura`
- `total_factura`
- OR `aviso_cliente = "NO SE DETECTAN DATOS DEL CLIENTE ESPERADO"`

### Common HIGH_Q Triggers
- Complex invoice headers (multiple sections)
- Low-quality scans (<300 DPI)
- Handwritten elements (signatures, notes)
- Multi-language invoices (English + Spanish)
- Merged cells (common in Spanish invoices)

---

## Field Extraction Schema (27 fields)

### Critical Fields (trigger HIGH_Q if empty)

| Field | Format | Notes |
|-------|--------|-------|
| `nombre_empresa` | UPPERCASE | Vendor name, not customer |
| `cif` | Strip "ES" prefix | `ES78971220F` -> `78971220F`, keep international prefixes |
| `fecha_expedicion` | DD/MM/YYYY | Spanish date format |
| `numero_factura` | Original format | Exclude REF/SKU/ART/PED columns |
| `total_factura` | `1.234,56` | Spanish number format (point=thousands, comma=decimals) |

### Tax Fields (Spanish IVA)

| Field | Description |
|-------|-------------|
| `base_21` / `iva_21` | 21% VAT (standard rate) |
| `base_10` / `iva_10` | 10% VAT (reduced rate) |
| `base_4` / `iva_4` | 4% VAT (super-reduced rate) |
| `exento` | VAT-exempt base |
| `recargo_52` | 5.2% surcharge (recargo de equivalencia) |
| `recargo_14` | 1.4% surcharge |
| `recargo_05` | 0.5% surcharge |
| `porcentaje_retencion` | IRPF withholding % (number only, no %) |
| `cuota_retencion` | IRPF withholding amount |

### Operation Type Fields

| Field | Value | When |
|-------|-------|------|
| `intra` | "SI" | Intra-EU operation |
| `isp` | (empty) | Manually filled by accountant |
| `extra` | "SI" | Extra-EU operation |

### Currency Fields (v1.6+)

| Field | Example |
|-------|---------|
| `moneda` | Always "EUR" (converted) |
| `moneda_origen` | "USD", "GBP", etc. |
| `tipo_cambio` | "0.92" |
| `fecha_tipo_cambio` | DD/MM/YYYY |

---

## CIF/NIF Normalization Rules

```
Spanish CIF:   "ES78971220F"   -> "78971220F"  (strip ES)
Spanish CIF:   "ESB93445385"   -> "B93445385"  (strip ES)
International: "LU20260743"    -> "LU20260743" (keep prefix)
International: "FR12345678901" -> "FR12345678901" (keep prefix)
```

## Number Formatting

- Spanish format: `1.234,56` (point for thousands, comma for decimals)
- NOT US format: `1,234.56`
- All monetary amounts use Spanish format
- Percentages: numbers only ("15" not "15%")
- Empty amounts: `""` (not "0" or "0,00")
- Negative values: `-1.234,56`

## Currency Conversion

Fixed rates (stored for audit):

| Currency | Rate to EUR |
|----------|-------------|
| USD | 0.92 |
| GBP | 1.17 |
| CHF | 1.08 |
| JPY | 0.0063 |
| CAD | 0.68 |
| AUD | 0.61 |
| CNY | 0.13 |

---

## n8n Code Patterns

### MySQL number conversion (Spanish -> SQL)

```javascript
// In Code node before MySQL INSERT
const toSqlNumber = (val) => {
  if (!val || val === '' || val === 'REVISAR') return null;
  return parseFloat(val.replace(/\./g, '').replace(',', '.'));
};
```

### Date conversion (DD/MM/YYYY -> YYYY-MM-DD)

```javascript
const toSqlDate = (val) => {
  if (!val || val === 'REVISAR') return null;
  const [d, m, y] = val.split('/');
  return `${y}-${m}-${d}`;
};
```

### Defensive field access after Loop/Merge

```javascript
// After transformation nodes, pairedItem chain breaks
(function() {
  try {
    return $('EditFields').first().json.output?.field || [];
  } catch(e) {
    return [];
  }
})()
```

---

## Database Schema (MySQL)

### OCR tracking fields

```sql
intentos_ocr TINYINT CHECK (intentos_ocr IN (1, 2))
  -- 1 = LOWCOST, 2 = HIGH_Q fallback
```

### Duplicate prevention

```sql
UNIQUE KEY (numero_factura, cif)
```

### Audit log events

```
OCR_LOWCOST_INICIADO / OCR_LOWCOST_EXITOSO / OCR_LOWCOST_INCOMPLETO
OCR_HIGH_Q_INICIADO / OCR_HIGH_Q_EXITOSO
VALIDACION_CLIENTE_OK / VALIDACION_CLIENTE_FALLIDA
```

---

## Production Stats (Q1 2026)

- 147 invoices processed in 3 months
- LOWCOST success rate: ~80% (no fallback needed)
- HIGH_Q triggered: ~20% of invoices
- Common HIGH_Q vendors: those with complex layouts, merged cells
- 6 issues detected and corrected (duplicates, missing fields)
- Total cost: 17.019,76 EUR processed (18 intracomunitarias, 3 ISP, 39 extracomunitarias)

## Optimization Tips

1. **Track which vendors always need HIGH_Q** - consider vendor-specific configs
2. **Use EU-west endpoint** for European documents (lower latency)
3. **Cache results** - same invoice format from same vendor rarely changes layout
4. **File renaming after processing** prevents re-submission (one-time retrieve)
5. **20-min schedule polling** from Google Drive is more reliable than webhooks for this use case
