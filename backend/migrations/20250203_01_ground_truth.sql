-- Migration: Create ground truth table for evaluation
-- depends: 20250116_01_evaluations

CREATE TABLE IF NOT EXISTS evaluation_ground_truth (
    id SERIAL PRIMARY KEY,
    filename VARCHAR NOT NULL,
    minio_object_key VARCHAR NOT NULL,  -- MinIO object key (e.g., "ground-truth/1_receipt.png")
    ground_truth JSONB NOT NULL,        -- TransactionModel as JSON
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_evaluation_ground_truth_filename ON evaluation_ground_truth(filename);
