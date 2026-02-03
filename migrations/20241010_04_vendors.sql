-- Migration: Create vendors tables
-- depends: 20241010_03_products

-- Apply
CREATE TABLE IF NOT EXISTS vendors (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS vendors_alternative_names (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    vendor INTEGER NOT NULL REFERENCES vendors(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_vendors_alternative_names_vendor ON vendors_alternative_names(vendor);
CREATE INDEX IF NOT EXISTS idx_vendors_alternative_names_name ON vendors_alternative_names(name);

-- Rollback (commented out - only for manual rollback reference)
-- DROP INDEX IF EXISTS idx_vendors_alternative_names_name;
-- DROP INDEX IF EXISTS idx_vendors_alternative_names_vendor;
-- DROP TABLE IF EXISTS vendors_alternative_names;
-- DROP TABLE IF EXISTS vendors;

