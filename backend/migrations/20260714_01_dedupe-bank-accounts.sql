-- depends: 20260630_01_bank-accounts

-- Merge any bank_accounts that share the same (name, bank_type) — e.g. the
-- default "Pekao SA" account created by the previous migration duplicated by
-- a manual "Dodaj konto" with the same defaults. Keep the oldest (lowest id)
-- account, move transactions to it, then drop the duplicates.
DO $$
DECLARE
    dup RECORD;
    keep_id INTEGER;
BEGIN
    FOR dup IN
        SELECT name, bank_type
        FROM bank_accounts
        GROUP BY name, bank_type
        HAVING COUNT(*) > 1
    LOOP
        SELECT MIN(id) INTO keep_id
        FROM bank_accounts
        WHERE name = dup.name AND bank_type = dup.bank_type;

        UPDATE bank_transactions
        SET account_id = keep_id
        WHERE account_id IN (
            SELECT id FROM bank_accounts
            WHERE name = dup.name AND bank_type = dup.bank_type AND id <> keep_id
        );

        DELETE FROM bank_accounts
        WHERE name = dup.name AND bank_type = dup.bank_type AND id <> keep_id;
    END LOOP;
END;
$$;

-- Prevent the same account from being registered twice going forward.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_bank_accounts_name_bank_type'
    ) THEN
        ALTER TABLE bank_accounts
        ADD CONSTRAINT uq_bank_accounts_name_bank_type UNIQUE (name, bank_type);
    END IF;
END;
$$;
