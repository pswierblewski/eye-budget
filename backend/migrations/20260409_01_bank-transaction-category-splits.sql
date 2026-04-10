-- depends: 20260227_01_bank_transactions

CREATE TABLE IF NOT EXISTS bank_transaction_category_splits (
    id                  SERIAL PRIMARY KEY,
    bank_transaction_id INTEGER NOT NULL
                            REFERENCES bank_transactions(id) ON DELETE CASCADE,
    category_id         INTEGER NOT NULL
                            REFERENCES categories(id) ON DELETE RESTRICT,
    amount              NUMERIC(12, 2) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_btcs_bank_transaction_id
    ON bank_transaction_category_splits(bank_transaction_id);
