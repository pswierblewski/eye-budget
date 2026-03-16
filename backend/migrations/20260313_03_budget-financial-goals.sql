-- depends: 20260313_02_budget-financial-focus

CREATE TABLE IF NOT EXISTS budget_financial_goals (
    id                        SERIAL PRIMARY KEY,
    name                      VARCHAR(200) NOT NULL,
    target_amount             NUMERIC(12,2) NOT NULL,
    target_date               DATE,
    priority_rank             INTEGER NOT NULL DEFAULT 0,
    monthly_allocation_amount NUMERIC(12,2) NOT NULL DEFAULT 0,
    accumulated_progress      NUMERIC(12,2) NOT NULL DEFAULT 0,
    is_active                 BOOLEAN NOT NULL DEFAULT TRUE,
    created_at                TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at                TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_budget_goals_is_active
    ON budget_financial_goals(is_active);
