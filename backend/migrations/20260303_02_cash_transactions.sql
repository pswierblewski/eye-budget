-- depends: 20260226_01_new-tables

-- Cash transactions entered manually or auto-created from receipt scans

CREATE TABLE IF NOT EXISTS cash_transactions (
    id              SERIAL PRIMARY KEY,
    booking_date    DATE NOT NULL,
    description     TEXT,
    amount          NUMERIC(12, 2) NOT NULL,   -- negative = expense, positive = income
    currency        VARCHAR(3) NOT NULL DEFAULT 'PLN',
    status          VARCHAR(32) NOT NULL DEFAULT 'to_confirm',   -- to_confirm | done
    category_id     INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    vendor_id       INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
    source          VARCHAR(16) NOT NULL DEFAULT 'manual',       -- manual | receipt
    receipt_scan_id INTEGER REFERENCES receipts_scans(id) ON DELETE SET NULL,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cash_transactions_status  ON cash_transactions(status);
CREATE INDEX IF NOT EXISTS idx_cash_transactions_booking ON cash_transactions(booking_date DESC);
CREATE INDEX IF NOT EXISTS idx_cash_transactions_vendor  ON cash_transactions(vendor_id);
CREATE INDEX IF NOT EXISTS idx_cash_transactions_tags    ON cash_transactions USING GIN (tags);

-- 1:1 link between a cash transaction and a receipt transaction
CREATE TABLE IF NOT EXISTS receipt_cash_links (
    id                      SERIAL PRIMARY KEY,
    cash_transaction_id     INTEGER NOT NULL UNIQUE
                                REFERENCES cash_transactions(id) ON DELETE CASCADE,
    receipt_transaction_id  INTEGER NOT NULL UNIQUE
                                REFERENCES receipt_transactions(id) ON DELETE CASCADE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rcl_cash_tx    ON receipt_cash_links(cash_transaction_id);
CREATE INDEX IF NOT EXISTS idx_rcl_receipt_tx ON receipt_cash_links(receipt_transaction_id);
