import pytest


@pytest.mark.integration
def test_find_similar_alternative_names_tolerates_ocr_diacritics(integration_app):
    # Arrange
    repo = integration_app.products_repository
    product_id = repo.insert_product("Mleko")
    repo.insert_alternative_name("MLEKO ŁACIĄTE 2% 1L C", product_id)

    # Act
    rows = repo.find_similar_alternative_names("MLEKO LACIATE 2% 1L C")

    # Assert
    assert rows
    assert rows[0][1] == product_id
    assert rows[0][2] >= 0.3


@pytest.mark.integration
def test_upsert_alternative_name_replaces_mapping(integration_app):
    # Arrange
    repo = integration_app.products_repository
    wrong = repo.insert_product("Ser")
    right = repo.insert_product("Masło")
    repo.insert_alternative_name("MASLO EXTRA 200G", wrong)

    # Act
    repo.upsert_alternative_name("MASLO EXTRA 200G", right)

    # Assert
    assert repo.get_product_by_alternative_name("MASLO EXTRA 200G") == right
