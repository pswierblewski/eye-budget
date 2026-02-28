-- Bank transactions imported from CSV exports (e.g. Pekao SA)

CREATE TABLE IF NOT EXISTS bank_transactions (
    id                  SERIAL PRIMARY KEY,
    reference_number    VARCHAR(128) UNIQUE NOT NULL,       -- deduplication key
    booking_date        DATE NOT NULL,
    value_date          DATE,
    counterparty        TEXT,
    counterparty_address TEXT,
    source_account      VARCHAR(64),
    target_account      VARCHAR(64),
    description         TEXT,
    amount              NUMERIC(12, 2) NOT NULL,
    currency            VARCHAR(3) NOT NULL DEFAULT 'PLN',
    operation_type      TEXT,
    status              VARCHAR(32) NOT NULL DEFAULT 'to_confirm',  -- to_confirm | done
    category_id         INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    category_candidates JSONB,
    vendor_id           INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_status   ON bank_transactions(status);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_booking  ON bank_transactions(booking_date DESC);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_vendor   ON bank_transactions(vendor_id);
