-- depends: 20260227_01_bank_transactions

CREATE TABLE IF NOT EXISTS receipt_bank_links (
    id                      SERIAL PRIMARY KEY,
    bank_transaction_id     INTEGER NOT NULL UNIQUE
                                REFERENCES bank_transactions(id) ON DELETE CASCADE,
    receipt_transaction_id  INTEGER NOT NULL UNIQUE
                                REFERENCES receipt_transactions(id) ON DELETE CASCADE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rbl_bank_tx    ON receipt_bank_links(bank_transaction_id);
CREATE INDEX IF NOT EXISTS idx_rbl_receipt_tx ON receipt_bank_links(receipt_transaction_id);
