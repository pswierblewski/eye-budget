-- depends: 20260309_01_drop-text-regions

ALTER TABLE receipts_scans ADD COLUMN IF NOT EXISTS text_regions JSONB;
