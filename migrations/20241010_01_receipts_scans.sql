-- Migration: Create receipts-scans table
-- depends:

-- Apply
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'receipt_status') THEN
        CREATE TYPE receipt_status AS ENUM ('new', 'processing', 'processed', 'failed', 'to_confirm', 'done');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS "receipts-scans" (
    id SERIAL PRIMARY KEY,
    filename VARCHAR NOT NULL UNIQUE,
    status receipt_status NOT NULL DEFAULT 'new',
    result JSONB,
    categories_candidates JSONB,
    category VARCHAR
);

-- Rollback
DROP TABLE IF EXISTS "receipts-scans";
DROP TYPE IF EXISTS receipt_status;

