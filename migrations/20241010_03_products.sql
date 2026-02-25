-- Migration: Create products tables
-- depends: 20241010_02_categories

CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products_alternative_names (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    product INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_products_alternative_names_product ON products_alternative_names(product);
CREATE INDEX IF NOT EXISTS idx_products_alternative_names_name ON products_alternative_names(name);
