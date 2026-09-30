import pytest
from unittest.mock import MagicMock

from src.data import ProductResolutionLLMItem, ProductResolutionsLLM
from src.services.product_resolver import ProductResolver


def _resolver(trgm=True):
    repo = MagicMock()
    repo.has_trigram_support.return_value = trgm
    repo.get_product_by_alternative_name.return_value = None
    repo.find_similar_alternative_names.return_value = []
    repo.get_names_by_ids.side_effect = lambda ids: {i: f"P{i}" for i in ids}
    service = MagicMock()
    return ProductResolver(repo, service), repo, service


@pytest.mark.unit
def test_exact_match_skips_llm():
    # Arrange
    resolver, repo, service = _resolver()
    repo.get_product_by_alternative_name.return_value = 5

    # Act
    result = resolver.resolve(["MLEKO"])

    # Assert
    assert result[0].product_id == 5
    assert result[0].method == "exact"
    assert result[0].normalized_name == "P5"
    service.resolve_products.assert_not_called()


@pytest.mark.unit
def test_high_similarity_is_auto_accepted_and_linked():
    # Arrange
    resolver, repo, service = _resolver()
    repo.find_similar_alternative_names.return_value = [("MLEKO ŁACIATE", 7, 0.9)]

    # Act
    result = resolver.resolve(["MLEKO LACIATE"])

    # Assert
    assert result[0].method == "fuzzy"
    assert result[0].product_id == 7
    repo.insert_alternative_name.assert_called_once_with("MLEKO LACIATE", 7)
    service.resolve_products.assert_not_called()


@pytest.mark.unit
def test_medium_similarity_goes_to_llm_and_accepts_listed_id():
    # Arrange
    resolver, repo, service = _resolver()
    repo.find_similar_alternative_names.return_value = [("SER GOUDA", 3, 0.5)]
    service.resolve_products.return_value = ProductResolutionsLLM(
        items=[ProductResolutionLLMItem(raw_name="SER EDAM", product_id=3)]
    )

    # Act
    result = resolver.resolve(["SER EDAM"])

    # Assert
    assert result[0].method == "llm_existing"
    assert result[0].product_id == 3
    repo.insert_alternative_name.assert_called_once_with("SER EDAM", 3)
    items = service.resolve_products.call_args[0][0]
    assert items[0][0] == "SER EDAM"
    assert [c.id for c in items[0][1]] == [3]


@pytest.mark.unit
def test_llm_id_outside_shortlist_is_treated_as_new():
    # Arrange
    resolver, repo, service = _resolver()
    repo.find_similar_alternative_names.return_value = [("SER GOUDA", 3, 0.5)]
    service.resolve_products.return_value = ProductResolutionsLLM(
        items=[ProductResolutionLLMItem(raw_name="SER EDAM", product_id=999, new_product_name="Ser")]
    )
    repo.get_product_by_name.return_value = None
    repo.insert_product.return_value = 12

    # Act
    result = resolver.resolve(["SER EDAM"])

    # Assert
    assert result[0].method == "llm_new"
    assert result[0].product_id == 12
    repo.insert_product.assert_called_once_with("Ser")


@pytest.mark.unit
def test_llm_new_reuses_existing_product_by_name():
    # Arrange
    resolver, repo, service = _resolver()
    service.resolve_products.return_value = ProductResolutionsLLM(
        items=[ProductResolutionLLMItem(raw_name="CHLEB ZYTNI", new_product_name="Chleb")]
    )
    repo.get_product_by_name.return_value = 2

    # Act
    result = resolver.resolve(["CHLEB ZYTNI"])

    # Assert
    assert result[0].product_id == 2
    repo.insert_product.assert_not_called()
    repo.insert_alternative_name.assert_called_once_with("CHLEB ZYTNI", 2)


@pytest.mark.unit
def test_llm_failure_leaves_products_unresolved():
    # Arrange
    resolver, repo, service = _resolver()
    service.resolve_products.side_effect = Exception("openai down")

    # Act
    result = resolver.resolve(["X"])

    # Assert
    assert result[0].method == "unresolved"
    assert result[0].product_id is None


@pytest.mark.unit
def test_duplicate_names_resolved_once_and_order_kept():
    # Arrange
    resolver, repo, service = _resolver()
    repo.get_product_by_alternative_name.side_effect = lambda n: {"RABAT": 1, "MLEKO": 2}[n]

    # Act
    result = resolver.resolve(["RABAT", "MLEKO", "RABAT"])

    # Assert
    assert [r.product_id for r in result] == [1, 2, 1]
    assert repo.get_product_by_alternative_name.call_count == 2


@pytest.mark.unit
def test_rapidfuzz_fallback_without_trigram():
    # Arrange
    resolver, repo, service = _resolver(trgm=False)
    repo.get_all_alternative_names.return_value = [("MLEKO ŁACIĄTE 2% 1L", 7), ("CHLEB", 8)]

    # Act
    similar = resolver.find_similar("MLEKO LACIATE 2% 1L")

    # Assert
    assert similar[0].product_id == 7
    assert 0.0 < similar[0].score <= 1.0
    repo.find_similar_alternative_names.assert_not_called()


@pytest.mark.unit
def test_trigram_error_switches_to_fallback():
    # Arrange
    resolver, repo, service = _resolver(trgm=True)
    repo.find_similar_alternative_names.side_effect = Exception("no similarity()")
    repo.get_all_alternative_names.return_value = [("CHLEB", 8)]

    # Act
    similar = resolver.find_similar("CHLEB")

    # Assert
    assert similar == []
    repo.get_all_alternative_names.assert_called_once()
