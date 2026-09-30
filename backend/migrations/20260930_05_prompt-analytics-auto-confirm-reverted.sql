-- depends: 20260930_04_receipts-scans-auto-confirm

ALTER TABLE prompt_analytics
    ADD COLUMN IF NOT EXISTS auto_confirm_reverted BOOLEAN NOT NULL DEFAULT FALSE;
