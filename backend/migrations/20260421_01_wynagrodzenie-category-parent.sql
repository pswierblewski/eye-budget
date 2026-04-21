-- depends: 20260413_01_bank-transaction-splits-unique

-- Parent income category for salary leaves (idempotent insert)
INSERT INTO categories (parent_id, name, c_type)
SELECT NULL, 'Wynagrodzenie', 'income'::category_type
WHERE NOT EXISTS (
    SELECT 1 FROM categories c
    WHERE c.name = 'Wynagrodzenie' AND c.parent_id IS NULL
);

-- Attach existing pensje under Wynagrodzenie (do not change category ids)
UPDATE categories child
SET parent_id = parent.id
FROM categories parent
WHERE parent.name = 'Wynagrodzenie'
  AND parent.parent_id IS NULL
  AND child.name IN ('Pensja Ada', 'Pensja Paweł')
  AND (child.parent_id IS DISTINCT FROM parent.id);
