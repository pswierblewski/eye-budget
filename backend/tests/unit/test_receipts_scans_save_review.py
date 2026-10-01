import pytest
from unittest.mock import MagicMock

from src.data import AutoConfirmWaiverItem
from src.repositories.receipts_scans import ReceiptsScansRepository
from tests.unit.test_receipts_scans_auto_confirm import _repo


@pytest.mark.unit
def test_set_category_selections_writes_json():
    # Arrange
    repo, cursor = _repo()
    mapping = {"MLEKO": 1}

    # Act
    ok = repo.set_category_selections(5, mapping)

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "category_selections = %s" in sql
    assert params[0].adapted == mapping
    assert params[1] == 5


@pytest.mark.unit
def test_append_auto_confirm_waiver_idempotent():
    # Arrange
    repo, cursor = _repo(fetchone=([{"code": "sum_mismatch", "product_name": None}],))
    item = AutoConfirmWaiverItem(code="sum_mismatch", product_name=None)

    # Act
    ok = repo.append_auto_confirm_waiver(5, item)

    # Assert
    assert ok is True
    assert cursor.execute.call_count == 1


@pytest.mark.unit
def test_append_auto_confirm_waiver_appends_new_entry():
    # Arrange
    repo, cursor = _repo(fetchone=([],))
    item = AutoConfirmWaiverItem(code="low_confidence", product_name="X")

    # Act
    ok = repo.append_auto_confirm_waiver(5, item)

    # Assert
    assert ok is True
    assert cursor.execute.call_count == 2
    update_sql, update_params = cursor.execute.call_args_list[1][0]
    assert "auto_confirm_waivers = %s" in update_sql
    assert update_params[0].adapted == [{"code": "low_confidence", "product_name": "X"}]


@pytest.mark.unit
def test_clear_save_review_fields():
    # Arrange
    repo, cursor = _repo()

    # Act
    ok = repo.clear_save_review_fields(7)

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "category_selections = NULL" in sql
    assert "auto_confirm_waivers = NULL" in sql
    assert params == (7,)
