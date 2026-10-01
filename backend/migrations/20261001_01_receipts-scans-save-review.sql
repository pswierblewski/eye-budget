-- depends: 20260930_05_prompt-analytics-auto-confirm-reverted

ALTER TABLE receipts_scans
    ADD COLUMN IF NOT EXISTS category_selections JSONB,
    ADD COLUMN IF NOT EXISTS auto_confirm_waivers JSONB;
