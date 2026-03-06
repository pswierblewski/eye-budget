-- depends: 20260306_02_remove_category_groups

CREATE TABLE IF NOT EXISTS prompt_analytics (
    id SERIAL PRIMARY KEY,
    scan_id INTEGER NOT NULL UNIQUE REFERENCES receipts_scans(id),
    vendor_name TEXT,
    category_corrections_count INTEGER NOT NULL DEFAULT 0,
    product_name_corrections_count INTEGER NOT NULL DEFAULT 0,
    ocr_product_count INTEGER NOT NULL DEFAULT 0,
    confirmed_product_count INTEGER NOT NULL DEFAULT 0,
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_prompt_analytics_scan_id ON prompt_analytics(scan_id);
CREATE INDEX IF NOT EXISTS idx_prompt_analytics_created_at ON prompt_analytics(created_at);
