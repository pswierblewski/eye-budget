-- Migration: Create receipts_scans table
-- depends:

DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'receipt_status') THEN
        CREATE TYPE receipt_status AS ENUM ('new', 'processing', 'processed', 'failed', 'to_confirm', 'done');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS receipts_scans (
    id SERIAL PRIMARY KEY,
    filename VARCHAR NOT NULL UNIQUE,
    status receipt_status NOT NULL DEFAULT 'new',
    result JSONB,
    categories_candidates JSONB,
    category VARCHAR
);
