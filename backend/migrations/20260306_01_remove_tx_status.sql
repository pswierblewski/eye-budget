ALTER TABLE bank_transactions DROP COLUMN IF EXISTS status;
DROP INDEX IF EXISTS idx_bank_transactions_status;

ALTER TABLE cash_transactions DROP COLUMN IF EXISTS status;
DROP INDEX IF EXISTS idx_cash_transactions_status;
