-- Migration: Create products tables
-- depends: 20241010_02_categories

-- Apply
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE products_alternative_names (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    product INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX idx_products_alternative_names_product ON products_alternative_names(product);
CREATE INDEX idx_products_alternative_names_name ON products_alternative_names(name);

-- Rollback
DROP INDEX IF EXISTS idx_products_alternative_names_name;
DROP INDEX IF EXISTS idx_products_alternative_names_product;
DROP TABLE IF EXISTS products_alternative_names;
DROP TABLE IF EXISTS products;

