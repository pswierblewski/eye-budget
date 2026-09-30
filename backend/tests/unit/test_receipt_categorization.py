import pytest
from unittest.mock import MagicMock

from src.data import ProductItem, TransactionModel
from src.services.product_resolver import ResolvedProduct, SimilarName
from src.services.receipt_auto_confirm import AutoConfirmSettings
from src.services.receipt_categorization import ReceiptCategorizationService

SETTINGS = AutoConfirmSettings(enabled=True)


def _tx(*names):
    return TransactionModel(
        vendor="Lidl",
        title="P",
        products=[ProductItem(name=n, quantity=1, price=1.0) for n in names],
        total=float(len(names)),
        date="2026-09-30",
    )


def _service(resolved, counts_by_call, ai_response=None, category_ids=None):
    resolver = MagicMock()
    resolver.resolve.return_value = resolved
    resolver.find_similar.return_value = []
    categories = MagicMock()
    categories.category_ids = category_ids if category_ids is not None else {1, 2, 3}
    categories.assign_category_candidates.return_value = ai_response or {"category_candidates": []}
    history = MagicMock()
    history.get_category_counts.side_effect = counts_by_call
    history.vendor_has_confirmed_receipts.return_value = True
    svc = ReceiptCategorizationService(resolver, categories, history, SETTINGS)
    return svc, resolver, categories, history


@pytest.mark.unit
def test_history_verdict_skips_llm():
    # Arrange
    resolved = [ResolvedProduct("MLEKO", 10, "Mleko", "exact", [])]
    svc, _, categories, _ = _service(resolved, [{10: {1: ("Nabiał", 5)}}])

    # Act
    result = svc.categorize(_tx("MLEKO"), vendor_id=3)

    # Assert
    categories.assign_category_candidates.assert_not_called()
    entry = result.candidates["category_candidates"][0]
    assert entry["source"] == "history"
    assert entry["history_count"] == 5
    assert entry["category_candidates"][0]["category_id"] == 1
    assert result.resolutions[0].source == "history"
    assert result.resolutions[0].category_id == 1
    assert result.vendor_has_history is True


@pytest.mark.unit
def test_products_without_verdict_go_to_llm_with_examples():
    # Arrange
    resolved = [
        ResolvedProduct("MLEKO", 10, "Mleko", "exact", []),
        ResolvedProduct("SER EDAM", 11, "Ser", "llm_existing", [SimilarName("SER GOUDA", 12, 0.6)]),
    ]
    ai = {
        "category_candidates": [
            {
                "product_name": "SER EDAM",
                "category_candidates": [
                    {"category_id": 1, "category_name": "Nabiał", "category_score": 0.95},
                    {"category_id": 2, "category_name": "Inne", "category_score": 0.05},
                ],
            }
        ]
    }
    svc, _, categories, _ = _service(
        resolved,
        [{10: {1: ("Nabiał", 5)}}, {12: {1: ("Nabiał", 3)}}],
        ai_response=ai,
    )

    # Act
    result = svc.categorize(_tx("MLEKO", "SER EDAM"), vendor_id=3)

    # Assert
    tx_arg = categories.assign_category_candidates.call_args[0][0]
    assert [p.name for p in tx_arg.products] == ["SER EDAM"]
    assert categories.assign_category_candidates.call_args.kwargs["examples"] == [("SER GOUDA", "Nabiał")]
    ai_resolution = result.resolutions[1]
    assert ai_resolution.source == "ai"
    assert ai_resolution.category_id == 1
    assert ai_resolution.confidence == pytest.approx(0.95)


@pytest.mark.unit
def test_ai_candidates_with_unknown_category_ids_are_dropped():
    # Arrange
    resolved = [ResolvedProduct("X", None, None, "unresolved", [])]
    ai = {
        "category_candidates": [
            {
                "product_name": "X",
                "category_candidates": [
                    {"category_id": 999, "category_name": "Halucynacja", "category_score": 0.99},
                ],
            }
        ]
    }
    svc, _, _, _ = _service(resolved, [{}, {}], ai_response=ai, category_ids={1, 2})

    # Act
    result = svc.categorize(_tx("X"), vendor_id=None)

    # Assert
    assert result.candidates["category_candidates"][0]["category_candidates"] == []
    assert result.resolutions[0].category_id is None


@pytest.mark.unit
def test_percent_scores_are_normalized():
    # Arrange
    resolved = [ResolvedProduct("X", None, None, "unresolved", [])]
    ai = {
        "category_candidates": [
            {
                "product_name": "X",
                "category_candidates": [
                    {"category_id": 1, "category_name": "Nabiał", "category_score": 91},
                ],
            }
        ]
    }
    svc, _, _, _ = _service(resolved, [{}, {}], ai_response=ai)

    # Act
    result = svc.categorize(_tx("X"), vendor_id=None)

    # Assert
    assert result.resolutions[0].confidence == pytest.approx(0.91)


@pytest.mark.unit
def test_duplicate_product_names_produce_one_entry():
    # Arrange
    resolved = [
        ResolvedProduct("RABAT", 1, "Rabat", "exact", []),
        ResolvedProduct("RABAT", 1, "Rabat", "exact", []),
    ]
    svc, _, _, _ = _service(resolved, [{1: {3: ("Rabaty", 4)}}])

    # Act
    result = svc.categorize(_tx("RABAT", "RABAT"), vendor_id=None)

    # Assert
    assert len(result.candidates["category_candidates"]) == 1
    assert len(result.resolutions) == 1
