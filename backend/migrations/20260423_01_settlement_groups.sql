-- depends: 20260421_01_wynagrodzenie-category-parent

CREATE TABLE settlement_groups (
    id          SERIAL PRIMARY KEY,
    title       TEXT,
    note        TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ
);

CREATE TABLE settlement_group_members (
    id                    SERIAL PRIMARY KEY,
    group_id              INTEGER NOT NULL
                              REFERENCES settlement_groups(id) ON DELETE CASCADE,
    bank_transaction_id   INTEGER
                              REFERENCES bank_transactions(id) ON DELETE CASCADE,
    cash_transaction_id   INTEGER
                              REFERENCES cash_transactions(id) ON DELETE CASCADE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (
        (bank_transaction_id IS NOT NULL AND cash_transaction_id IS NULL)
        OR
        (bank_transaction_id IS NULL AND cash_transaction_id IS NOT NULL)
    )
);

CREATE UNIQUE INDEX uq_sgm_bank ON settlement_group_members (bank_transaction_id)
    WHERE bank_transaction_id IS NOT NULL;
CREATE UNIQUE INDEX uq_sgm_cash ON settlement_group_members (cash_transaction_id)
    WHERE cash_transaction_id IS NOT NULL;

CREATE INDEX idx_sgm_group ON settlement_group_members (group_id);
