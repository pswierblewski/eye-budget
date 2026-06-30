-- depends: 20260409_01_bank-transaction-category-splits

CREATE TABLE IF NOT EXISTS bank_accounts (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    bank_type  VARCHAR(50)  NOT NULL,   -- 'pekao' | 'revolut' | 'other'
    color      VARCHAR(20)  NOT NULL DEFAULT 'blue',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE bank_transactions
ADD COLUMN IF NOT EXISTS account_id INTEGER REFERENCES bank_accounts(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_bank_transactions_account ON bank_transactions(account_id);

-- Migrate existing transactions to a default Pekao SA account
DO $$
DECLARE
    default_account_id INTEGER;
BEGIN
    IF EXISTS (SELECT 1 FROM bank_transactions WHERE account_id IS NULL LIMIT 1) THEN
        INSERT INTO bank_accounts (name, bank_type, color)
        VALUES ('Pekao SA', 'pekao', 'blue')
        RETURNING id INTO default_account_id;

        UPDATE bank_transactions SET account_id = default_account_id WHERE account_id IS NULL;
    END IF;
END;
$$;
