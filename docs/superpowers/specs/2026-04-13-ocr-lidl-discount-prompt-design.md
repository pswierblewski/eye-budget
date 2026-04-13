# OCR Prompt: Lidl Discount Pattern Handling

**Date:** 2026-04-13  
**Branch:** 009-bank-transaction-category-splits  
**File changed:** `backend/src/services/ocr.py`

## Problem

The OCR prompt in `OCRService.__init__()` handles two discount patterns explicitly:
- `Uwzgl. rabat: -X,XX st. c Y,YY` (inline rabat with original price)
- `Rabat <name>` (standalone rabat line)

It does **not** mention Lidl-specific discount line types:
- `Lidl Plus kupon` — loyalty coupon discount
- `Lidl Plus voucher` — loyalty voucher discount
- `Taniej za 2` / `Taniej z 2` — multi-buy promotion ("cheaper by 2")

Without explicit guidance, the model can occasionally classify one of these lines as a regular purchased product (positive price) instead of a discount entry.

## Design

### Change

Add one bullet to section 4 of the prompt, inserted before the closing summary line:

```python
"   - Loyalty-card discounts (e.g. 'Lidl Plus kupon', 'Lidl Plus voucher') and multi-buy promotions "
"     (e.g. 'Taniej za 2', 'Taniej z 2') always carry a negative price — add each as a separate "
"     product entry. Never assign a positive price to a line that is clearly a discount or promotion. "
```

### Rationale

Approach C (specific examples + general principle):
- Concrete names anchor the model on the exact Lidl patterns seen in production
- General principle ("clearly a discount or promotion") covers future variants without another prompt update
- No schema changes needed — discounts already belong in the `products` list with negative prices per the existing `ProductItem` and `TransactionModel` design

### Expected output (unchanged structure)

Discount entries continue to appear as separate `ProductItem` entries:
```json
{ "name": "Lidl Plus kupon",   "price": -5.90, "quantity": 1, "unit_price": null }
{ "name": "Lidl Plus voucher", "price": -0.35, "quantity": 1, "unit_price": null }
{ "name": "Taniej za 2",       "price": -0.58, "quantity": 1, "unit_price": null }
```

## Scope

- **In scope:** one prompt string addition in `ocr.py`
- **Out of scope:** schema changes, new discount type field, UI changes
