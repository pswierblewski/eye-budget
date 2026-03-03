-- depends: 20260227_02_bank_receipt_links

-- Add freeform tags to receipts and bank transactions
ALTER TABLE receipts_scans
    ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';

ALTER TABLE bank_transactions
    ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_receipts_scans_tags ON receipts_scans USING GIN (tags);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_tags ON bank_transactions USING GIN (tags);
