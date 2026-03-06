-- Migration: Remove category_groups table and category_group_id from categories
-- depends: 20241010_02_categories

-- Drop FK constraint from categories.category_group_id
ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_category_group_id_fkey;

-- Drop category_group_id column from categories
ALTER TABLE categories DROP COLUMN IF EXISTS category_group_id;

-- Drop the category_groups table
DROP TABLE IF EXISTS category_groups;

-- Replace insert_category function to no longer use group_name
CREATE OR REPLACE FUNCTION insert_category(
    parent_name TEXT,
    category_name TEXT,
    group_name TEXT,
    ctype category_type DEFAULT 'expense'
) RETURNS VOID AS $$
DECLARE
    parent_id_int INT;
    existing_category_id INT;
BEGIN
    IF parent_name IS NOT NULL THEN
        SELECT id INTO parent_id_int FROM categories
        WHERE name = parent_name AND parent_id IS NULL;
    ELSE
        parent_id_int := NULL;
    END IF;

    SELECT id INTO existing_category_id FROM categories
    WHERE name = category_name
    AND (parent_id = parent_id_int OR (parent_id IS NULL AND parent_id_int IS NULL));

    IF existing_category_id IS NULL THEN
        INSERT INTO categories (parent_id, name, c_type)
        VALUES (parent_id_int, category_name, ctype);
    END IF;
END;
$$ LANGUAGE plpgsql;
