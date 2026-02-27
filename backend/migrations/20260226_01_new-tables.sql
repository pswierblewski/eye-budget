-- depends: 20260225_01_client_syncs

-- Fix set_status() bug: message column was referenced in code but never created
-- Add minio_object_key for image serving
-- Drop legacy category column
ALTER TABLE receipts_scans
    ADD COLUMN IF NOT EXISTS message TEXT,
    ADD COLUMN IF NOT EXISTS minio_object_key VARCHAR,
    DROP COLUMN IF EXISTS category;

-- Confirmed receipt transactions (created when user confirms categories in review UI)
CREATE TABLE receipt_transactions (
    id              SERIAL PRIMARY KEY,
    scan_id         INTEGER NOT NULL REFERENCES receipts_scans(id),
    vendor_id       INTEGER REFERENCES vendors(id),
    raw_vendor_name VARCHAR NOT NULL,
    date            DATE NOT NULL,
    total           NUMERIC(10,2) NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Line items for each confirmed transaction
CREATE TABLE receipt_transaction_items (
    id               SERIAL PRIMARY KEY,
    transaction_id   INTEGER NOT NULL REFERENCES receipt_transactions(id) ON DELETE CASCADE,
    product_id       INTEGER REFERENCES products(id),
    raw_product_name VARCHAR NOT NULL,
    category_id      INTEGER NOT NULL REFERENCES categories(id),
    quantity         NUMERIC(10,3) NOT NULL,
    unit_price       NUMERIC(10,2),
    price            NUMERIC(10,2) NOT NULL
);

CREATE INDEX idx_receipt_transactions_scan_id ON receipt_transactions(scan_id);
CREATE INDEX idx_receipt_transaction_items_transaction_id ON receipt_transaction_items(transaction_id);
