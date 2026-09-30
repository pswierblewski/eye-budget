-- depends: 20260930_03_pg-trgm

ALTER TABLE receipts_scans
    ADD COLUMN IF NOT EXISTS confirmation_source TEXT,
    ADD COLUMN IF NOT EXISTS auto_confirm_reasons JSONB;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'receipts_scans_confirmation_source_check'
    ) THEN
        ALTER TABLE receipts_scans
            ADD CONSTRAINT receipts_scans_confirmation_source_check
            CHECK (confirmation_source IS NULL OR confirmation_source IN ('manual', 'auto'));
    END IF;
END $$;

UPDATE receipts_scans SET confirmation_source = 'manual'
WHERE status = 'done' AND confirmation_source IS NULL;
