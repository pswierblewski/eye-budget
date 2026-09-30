import json
import pytest
from unittest.mock import MagicMock

from src.data import NormalizedProductItem, ProductItem, TransactionModel
from src.services.categories import CategoriesService
from src.services.products import ProductsService


def _client_returning(arguments: dict) -> MagicMock:
    client = MagicMock()
    call = MagicMock()
    call.type = "function_call"
    call.arguments = json.dumps(arguments)
    client.responses.create.return_value.output = [call]
    return client


def _prompt_text(client: MagicMock) -> str:
    kwargs = client.responses.create.call_args.kwargs
    return kwargs["input"][0]["content"][0]["text"]


@pytest.mark.unit
def test_resolve_products_lists_candidates_and_parses_response():
    # Arrange
    client = _client_returning({"items": [{"raw_name": "MLEKO 2%", "product_id": 4, "new_product_name": None}]})
    svc = ProductsService(client=client)

    # Act
    result = svc.resolve_products([("MLEKO 2%", [NormalizedProductItem(id=4, name="Mleko")])])

    # Assert
    assert result.items[0].product_id == 4
    text = _prompt_text(client)
    assert "MLEKO 2%" in text
    assert "[4] Mleko" in text


@pytest.mark.unit
def test_resolve_products_marks_missing_candidates():
    # Arrange
    client = _client_returning({"items": [{"raw_name": "SER KOZI", "product_id": None, "new_product_name": "Ser kozi"}]})
    svc = ProductsService(client=client)

    # Act
    result = svc.resolve_products([("SER KOZI", [])])

    # Assert
    assert result.items[0].new_product_name == "Ser kozi"
    assert "SER KOZI | kandydaci: brak" in _prompt_text(client)


@pytest.mark.unit
def test_resolve_products_raises_without_function_call():
    # Arrange
    client = MagicMock()
    client.responses.create.return_value.output = []
    svc = ProductsService(client=client)

    # Act / Assert
    with pytest.raises(ValueError):
        svc.resolve_products([("X", [])])


@pytest.mark.unit
def test_assign_category_candidates_appends_examples():
    # Arrange
    client = _client_returning({"category_candidates": []})
    svc = CategoriesService(db_context=MagicMock(), client=client)
    svc.categories = "| category_id |"
    tx = TransactionModel(vendor="Lidl", title="P", products=[ProductItem(name="SER", quantity=1, price=5)], total=5, date="2026-09-30")

    # Act
    svc.assign_category_candidates(tx, examples=[("SER GOUDA 150G", "Nabiał")])

    # Assert
    text = _prompt_text(client)
    assert "- SER GOUDA 150G -> Nabiał" in text


@pytest.mark.unit
def test_assign_category_candidates_without_examples_has_no_examples_block():
    # Arrange
    client = _client_returning({"category_candidates": []})
    svc = CategoriesService(db_context=MagicMock(), client=client)
    tx = TransactionModel(vendor="Lidl", title="P", products=[ProductItem(name="SER", quantity=1, price=5)], total=5, date="2026-09-30")

    # Act
    svc.assign_category_candidates(tx)

    # Assert
    assert "Previously confirmed" not in _prompt_text(client)


@pytest.mark.unit
def test_build_collects_category_ids():
    # Arrange
    svc = CategoriesService(db_context=MagicMock(), client=MagicMock())
    svc.categories_repository = MagicMock()
    svc.categories_repository.get_categories.return_value = [(1, "Nabiał", "Jedzenie"), (2, "Pieczywo", "Jedzenie")]

    # Act
    svc.build()

    # Assert
    assert svc.category_ids == {1, 2}
    assert "Nabiał" in svc.categories
