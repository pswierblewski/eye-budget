-- depends: 20260226_01_new-tables

-- rollback: DROP TABLE IF EXISTS task_runs;

CREATE TABLE IF NOT EXISTS task_runs (
    id          SERIAL PRIMARY KEY,
    task_id     VARCHAR(64)  NOT NULL UNIQUE,
    task_type   VARCHAR(32)  NOT NULL,   -- 'process_receipts' | 'run_evaluation'
    status      VARCHAR(16)  NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMP    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_task_runs_task_id ON task_runs (task_id);
