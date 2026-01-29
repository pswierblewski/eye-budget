-- Migration: Create evaluation tables
-- depends: 20241010_04_vendors

-- Apply

-- Evaluation runs table (stores summary of each evaluation run)
CREATE TABLE IF NOT EXISTS evaluation_runs (
    id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP DEFAULT NOW(),
    model_used VARCHAR NOT NULL,
    total_files INT NOT NULL,
    successful INT NOT NULL,
    failed INT NOT NULL,
    success_rate FLOAT,
    avg_processing_time_ms FLOAT,
    avg_field_completeness FLOAT,
    avg_consistency_rate FLOAT,
    config JSONB
);

-- Individual file results (stores metrics for each processed file)
CREATE TABLE IF NOT EXISTS evaluation_results (
    id SERIAL PRIMARY KEY,
    run_id INT REFERENCES evaluation_runs(id) ON DELETE CASCADE,
    filename VARCHAR NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    processing_time_ms INT,
    -- Extraction metrics
    fields_extracted INT,
    field_completeness FLOAT,
    product_count INT,
    has_vendor BOOLEAN,
    has_date BOOLEAN,
    has_total BOOLEAN,
    -- Consistency metrics
    products_sum FLOAT,
    extracted_total FLOAT,
    total_difference FLOAT,
    is_consistent BOOLEAN,
    -- Full result for analysis
    result JSONB
);

-- Index for faster lookups by run_id
CREATE INDEX IF NOT EXISTS idx_evaluation_results_run_id ON evaluation_results(run_id);

-- Rollback
-- DROP INDEX IF EXISTS idx_evaluation_results_run_id;
-- DROP TABLE IF EXISTS evaluation_results;
-- DROP TABLE IF EXISTS evaluation_runs;
