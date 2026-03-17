-- depends: 20260313_04_budget-simulations

CREATE TABLE IF NOT EXISTS budget_ai_recommendations (
    id                   SERIAL PRIMARY KEY,
    generated_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    data_through_date    DATE NOT NULL,
    recommendations_json JSONB NOT NULL DEFAULT '[]',
    is_current           BOOLEAN NOT NULL DEFAULT TRUE,
    months_of_data       INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_budget_ai_recs_is_current
    ON budget_ai_recommendations(is_current);
CREATE INDEX IF NOT EXISTS idx_budget_ai_recs_generated_at
    ON budget_ai_recommendations(generated_at DESC);
