-- depends: 20260930_01_fix-empty-receipt-result-dates

ALTER TABLE receipts_scans
  ADD COLUMN IF NOT EXISTS ocr_raw JSONB;
