-- Migration: Create client_syncs table for tracking receipt sync state per budget client
-- depends: 20241010_01_receipts_scans

CREATE TABLE IF NOT EXISTS client_syncs (
    id SERIAL PRIMARY KEY,
    receipt_scan_id INTEGER NOT NULL REFERENCES receipts_scans(id),
    client_name VARCHAR NOT NULL,
    external_id VARCHAR,            -- ID returned by the client (e.g. MyMoney transaction ID)
    status VARCHAR NOT NULL DEFAULT 'synced',
    synced_at TIMESTAMP NOT NULL DEFAULT NOW(),
    error_message TEXT,
    UNIQUE (receipt_scan_id, client_name)
);

CREATE INDEX IF NOT EXISTS idx_client_syncs_receipt_scan_id ON client_syncs(receipt_scan_id);
CREATE INDEX IF NOT EXISTS idx_client_syncs_client_name ON client_syncs(client_name);
