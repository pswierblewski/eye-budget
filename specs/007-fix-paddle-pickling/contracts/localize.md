# Contract: POST /receipts/{scan_id}/localize

**Feature**: 007-fix-paddle-pickling  
**Status**: Existing endpoint — contract UNCHANGED by this fix

## Overview

Runs (or re-runs) PaddleOCR text localization for a stored receipt image and returns bounding-box polygons matched to each product in the LLM result.

## Request

```
POST /receipts/{scan_id}/localize
```

| Parameter | Location | Type | Description |
|-----------|----------|------|-------------|
| `scan_id` | path | integer | ID of the receipt scan |

No request body.

## Response — 200 OK

```json
{
  "image_width": 800,
  "image_height": 1200,
  "product_regions": {
    "0": { "polygon": [[10, 20], [200, 20], [200, 40], [10, 40]] },
    "1": { "polygon": [[10, 50], [180, 50], [180, 70], [10, 70]] }
  }
}
```

Keys in `product_regions` are 0-based string indices matching the order of `products` in the receipt scan result.

## Error Responses

| Status | Condition |
|--------|-----------|
| 404 | Scan not found, not yet processed, or has no stored image in MinIO |
| 500 | Unexpected error during OCR or result parsing (was previously always triggered by pickle error — this fix resolves it) |

## Backend layers

| Layer | File | Notes |
|-------|------|-------|
| Route | `backend/src/main.py:350` | `localize_receipt(scan_id)` |
| App method | `backend/src/app.py:828` | Downloads image, calls `_run_localization` |
| Service | `backend/src/services/text_localization.py` | `TextLocalizationService.detect()` — calls `_ocr_worker` in subprocess |
| Response model | `backend/src/data.py:213` | `TextRegionsResult` |

No frontend proxy route or `lib/api.ts` function changes — the fix is backend-internal only.
