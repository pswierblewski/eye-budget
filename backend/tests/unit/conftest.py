from unittest.mock import MagicMock
from src.app import App

ALL_PARAMS = [
    # db context — must be mocked to prevent psycopg2.connect() during unit tests
    "eye_budget_db_context",
    # repositories
    "files_repository",
    "receipts_scans_repository",
    "evaluations_repository",
    "ground_truth_repository",
    "vendors_repository",
    "products_repository",
    "transactions_repository",
    "categories_repository",
    "bank_transactions_repository",
    "bank_receipt_links_repository",
    "bank_transaction_splits_repository",
    "cash_transactions_repository",
    "cash_receipt_links_repository",
    "unified_transactions_repository",
    "settlement_groups_repository",
    "prompt_analytics_repository",
    "budget_analysis_repository",
    "budget_simulations_repository",
    # services
    "ocr_service",
    "preprocessing_service",
    "minio_service",
    "text_localization_service",
    "text_matching_service",
    "vendors_service",
    "products_service",
    "categories_service",
    "bank_categorization_service",
    "bank_csv_parser",
    "budget_analysis_service",
    "budget_simulation_service",
    "evaluation_service",
    "ground_truth_service",
]


def make_app(**overrides):
    defaults = {p: MagicMock() for p in ALL_PARAMS}
    defaults.update(overrides)
    return App(**defaults)
