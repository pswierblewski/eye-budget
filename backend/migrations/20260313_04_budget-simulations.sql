-- depends: 20260313_03_budget-financial-goals

CREATE TABLE IF NOT EXISTS budget_simulations (
    id                  SERIAL PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    expense_name        VARCHAR(200) NOT NULL,
    expense_amount      NUMERIC(12,2) NOT NULL,
    expense_type        VARCHAR(20) NOT NULL CHECK (expense_type IN ('one_time', 'recurring')),
    expense_start_date  DATE NOT NULL,
    status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'processing', 'done', 'failed')),
    result_json         JSONB,
    error_message       TEXT,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_budget_simulations_status
    ON budget_simulations(status);
CREATE INDEX IF NOT EXISTS idx_budget_simulations_created_at
    ON budget_simulations(created_at DESC);
