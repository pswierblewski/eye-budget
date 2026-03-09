-- depends: 20260307_01_add-text-regions

ALTER TABLE receipts_scans DROP COLUMN IF EXISTS text_regions;
