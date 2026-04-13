-- depends: 20260409_01_bank-transaction-category-splits

ALTER TABLE bank_transaction_category_splits
    ADD CONSTRAINT uq_btcs_tx_category
    UNIQUE (bank_transaction_id, category_id);
