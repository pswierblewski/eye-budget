-- depends: 20260306_03_prompt_analytics

ALTER TABLE receipts_scans ADD COLUMN IF NOT EXISTS text_regions JSONB;
