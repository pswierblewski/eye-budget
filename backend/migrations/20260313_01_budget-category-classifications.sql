-- depends: 20260310_01_readd-text-regions

CREATE TABLE IF NOT EXISTS budget_category_classifications (
    id               SERIAL PRIMARY KEY,
    category_id      INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    classification   VARCHAR(20) NOT NULL CHECK (classification IN ('essential', 'discretionary')),
    is_user_override BOOLEAN NOT NULL DEFAULT FALSE,
    created_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_budget_category_classifications_category UNIQUE (category_id)
);

CREATE INDEX IF NOT EXISTS idx_budget_cat_class_category_id
    ON budget_category_classifications(category_id);
