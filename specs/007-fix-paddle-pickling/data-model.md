# Data Model: Fix PaddleOCR Serialization Error

**Feature**: 007-fix-paddle-pickling  
**Date**: 2026-04-01

## No schema changes

This feature introduces no new database tables, migrations, or Pydantic model changes.

## Existing types affected (unchanged)

### `OcrLine` (`backend/src/services/text_localization.py`)

```
OcrLine = tuple[list[list[int]], str, float]
         ─────────────────────  ───  ─────
         polygon (4×[x,y])      text  score
```

`_to_serializable()` produces data that `_parse_result()` converts into `OcrLine` tuples. The type is unchanged.

### `TextRegionsResult` / `TextRegion` (`backend/src/data.py`)

The Pydantic response model for `POST /receipts/{id}/localize`. Unchanged — the fix does not alter the API contract.

## Internal wire format (subprocess → main process)

`_to_serializable()` produces plain Python lists in legacy shape before they cross the process boundary:

```
[                          # list of pages
  [                        # page = list of items
    [                      # item
      [[x,y],[x,y],[x,y],[x,y]],   # polygon: list[list[int]]
      [str, float]                  # [text, score]
    ],
    ...
  ],
  ...
]
```

This is the same shape as `_CANNED_PADDLE_RESULT` used in existing tests — no test fixture changes needed.
