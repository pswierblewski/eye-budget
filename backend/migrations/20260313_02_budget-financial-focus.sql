-- depends: 20260313_01_budget-category-classifications

CREATE TABLE IF NOT EXISTS budget_financial_focus (
    id          SERIAL PRIMARY KEY,
    label       VARCHAR(200) NOT NULL,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP NOT NULL DEFAULT NOW()
);
