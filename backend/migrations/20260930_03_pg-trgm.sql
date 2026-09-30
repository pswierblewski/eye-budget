-- depends: 20260930_02_receipts-scans-ocr-raw

-- pg_trgm may be unavailable on a managed Postgres without CREATE privileges;
-- the application falls back to rapidfuzz in that case.
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS pg_trgm;
EXCEPTION
    WHEN insufficient_privilege OR undefined_file THEN
        RAISE NOTICE 'pg_trgm not available: %', SQLERRM;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
        CREATE INDEX IF NOT EXISTS idx_products_alternative_names_name_trgm
            ON products_alternative_names USING gin (name gin_trgm_ops);
    END IF;
END $$;
