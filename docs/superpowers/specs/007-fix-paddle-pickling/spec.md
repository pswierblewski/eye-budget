# Feature Specification: Fix PaddleOCR Serialization Error

**Feature Branch**: `007-fix-paddle-pickling`  
**Created**: 2026-04-01  
**Status**: Draft  
**Input**: User description: "Dodana zmiana _to_serializable() do backend/services/text_localization.py — konwersja wynikow PaddleOCR na serializowalne struktury Pythona, aby naprawic blad pickle przy komunikacji ProcessPoolExecutor. Zmiana musi byc otestowana (unit testy) i wdrozena przez pelny pipeline CI/CD."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Receipt text localization returns bounding boxes (Priority: P1)

A user uploads a receipt and triggers text localization (`POST /receipts/{id}/localize`). The backend runs PaddleOCR in a separate subprocess and returns polygon coordinates for each detected text region. Previously this endpoint returned HTTP 500 due to a serialization error — after this fix it must return 200 with bounding-box data.

**Why this priority**: This is the core broken behaviour. Everything else (CI/CD, tests) exists to protect this fix from regressing.

**Independent Test**: Send `POST /receipts/{id}/localize` for a receipt that has an image stored in MinIO. Verify the response is HTTP 200 and contains a non-empty `regions` array with polygon coordinates.

**Acceptance Scenarios**:

1. **Given** a receipt scan with a processed image, **When** `POST /receipts/{id}/localize` is called, **Then** the response is HTTP 200 with a list of text regions containing polygons, text, and confidence scores.
2. **Given** the same request, **When** PaddleOCR returns a new dict-based result format (PaddleOCR ≥ 2.10), **Then** the result is correctly parsed and returned without error.
3. **Given** the same request, **When** PaddleOCR returns the legacy list-of-lists format, **Then** the result is also correctly parsed and returned without error.

---

### User Story 2 - Bounding boxes visible on receipt image in the UI (Priority: P2)

A user viewing a processed receipt in the frontend sees text-region overlays drawn on the receipt image. Previously the overlays were absent because the localization endpoint was failing with HTTP 500.

**Why this priority**: This is the visible symptom that prompted the bug report. It depends on P1 being fixed first.

**Independent Test**: Open a processed receipt in the app, trigger localization. Confirm polygon overlays appear on the receipt image.

**Acceptance Scenarios**:

1. **Given** a processed receipt page, **When** the user triggers text localization, **Then** polygon overlays appear on the receipt image for all detected text lines.
2. **Given** an empty OCR result (e.g. blank image), **When** localization is triggered, **Then** the response is HTTP 200 with an empty `regions` array and no overlay is drawn.

---

### Edge Cases

- PaddleOCR returns `None` or an empty list — system must return an empty regions list, not an error.
- PaddleOCR result object contains pages with `None` entries — each `None` page must be skipped gracefully.
- Individual polygon coordinate conversion fails due to malformed point data — that line must be skipped; remaining lines must still be returned.
- `ProcessPoolExecutor` subprocess crashes (BrokenProcessPool) — existing retry logic must reset the executor and retry once before raising.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The OCR subprocess MUST convert PaddleOCR results to plain, picklable Python structures before returning them across the process boundary.
- **FR-002**: The conversion MUST handle both the new dict-based PaddleOCR ≥ 2.10 result format (`rec_texts`, `rec_polys`/`dt_polys`, `rec_scores`) and the legacy list-of-lists format.
- **FR-003**: The conversion MUST handle `None` or empty result pages without raising exceptions.
- **FR-004**: The `POST /receipts/{id}/localize` endpoint MUST return HTTP 200 with polygon data when PaddleOCR successfully processes the image.
- **FR-005**: The change MUST be covered by unit tests verifying correct conversion for: new dict format, legacy list format, `None` result, and empty-page result.
- **FR-006**: All existing tests MUST continue to pass after the change.
- **FR-007**: The fix MUST be deployed to the production server via the existing CI/CD pipeline — no manual hot-patching.

### Key Entities

- **TextRegionsResult**: The structured response returned by `/localize` — contains a list of regions, each with a polygon (list of `[x, y]` points), text string, and confidence score.
- **OCR Worker subprocess**: A spawned process that owns the PaddleOCR singleton; its return value must be serializable for cross-process transfer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `POST /receipts/{id}/localize` returns HTTP 200 (not 500) for any receipt with a stored image.
- **SC-002**: The response contains at least one text region with a valid polygon for a non-blank receipt image.
- **SC-003**: All new unit tests for the conversion function pass (100% green).
- **SC-004**: The full backend test suite (existing + new tests) passes in CI without regressions.
- **SC-005**: The fix is live on the production server within one successful CI/CD pipeline run after merge to `master`.

## Assumptions

- The root cause is confirmed: PaddleOCR ≥ 2.10 returns result objects containing non-picklable internal references (`CopyableWeakMethod`), which break cross-process serialization in `ProcessPoolExecutor`.
- The existing result-parsing logic in `TextLocalizationService` handles both result formats correctly once the data is plain Python structures — no changes are needed there.
- MinIO images for already-processed receipts are accessible; this fix does not address missing-image scenarios.
- No frontend changes are required — the API contract for `/localize` remains unchanged.
