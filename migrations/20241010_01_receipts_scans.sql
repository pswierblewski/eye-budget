-- Migration: Create receipts-scans table
-- depends:

-- Apply
CREATE TYPE receipt_status AS ENUM ('new', 'processing', 'processed', 'failed', 'to_confirm', 'done');

CREATE TABLE "receipts-scans" (
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

