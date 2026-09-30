import pytest
from unittest.mock import MagicMock

from src.data import ReceiptsScanStatus
from src.repositories.prompt_analytics import PromptAnalyticsRepository
from src.repositories.receipts_scans import ReceiptsScansRepository


def _repo(cls=ReceiptsScansRepository, fetchone=None, fetchall=None):
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall or []
    repo = cls.__new__(cls)
    repo.conn = conn
    repo.table = "receipts_scans"
    return repo, cursor


@pytest.mark.unit
def test_set_status_done_records_source():
    # Arrange
    repo, cursor = _repo()

    # Act
    repo.set_status_done(5, "auto")

    # Assert
    sql, params = cursor.execute.call_args[0]
    assert "confirmation_source = %s" in sql
    assert params == (ReceiptsScanStatus.DONE, "auto", 5)


@pytest.mark.unit
def test_set_status_done_defaults_to_manual():
    # Arrange
    repo, cursor = _repo()

    # Act
    repo.set_status_done(5)

    # Assert
    assert cursor.execute.call_args[0][1] == (ReceiptsScanStatus.DONE, "manual", 5)


@pytest.mark.unit
def test_set_status_to_confirm_clears_source():
    # Arrange
    repo, cursor = _repo()

    # Act
    repo.set_status_to_confirm_by_id(5)

    # Assert
    assert "confirmation_source = NULL" in cursor.execute.call_args[0][0]


@pytest.mark.unit
def test_set_auto_confirm_reasons_writes_json():
    # Arrange
    repo, cursor = _repo()
    reasons = [{"code": "sum_mismatch", "message": "m", "blocking": True}]

    # Act
    ok = repo.set_auto_confirm_reasons(5, reasons)

    # Assert
    assert ok is True
    _, params = cursor.execute.call_args[0]
    assert params[0].adapted == reasons
    assert params[1] == 5


@pytest.mark.unit
def test_set_category_candidates_if_pending_true_when_row_updated():
    # Arrange
    repo, cursor = _repo(fetchone=(5,))

    # Act
    ok = repo.set_category_candidates_if_pending(5, {"category_candidates": []})

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "status = %s" in sql
    assert params[1:] == (5, ReceiptsScanStatus.TO_CONFIRM)


@pytest.mark.unit
def test_set_category_candidates_if_pending_false_when_status_changed():
    # Arrange
    repo, _ = _repo(fetchone=None)

    # Act / Assert
    assert repo.set_category_candidates_if_pending(5, {}) is False


@pytest.mark.unit
def test_get_pending_for_rescore_parses_results():
    # Arrange
    good = {"vendor": "Lidl", "date": "2026-09-30", "title": "P", "total": 1.0, "products": []}
    repo, cursor = _repo(fetchall=[(1, "a.jpg", good), (2, "b.jpg", {"broken": True})])

    # Act
    scans = repo.get_pending_for_rescore()

    # Assert
    assert [s.id for s in scans] == [1]
    assert cursor.execute.call_args[0][1] == (ReceiptsScanStatus.TO_CONFIRM,)


@pytest.mark.unit
def test_get_by_id_reads_confirmation_fields():
    # Arrange
    repo, _ = _repo(
        fetchone=(
            1,
            "a.jpg",
            "done",
            None,
            None,
            None,
            [],
            None,
            None,
            None,
            "auto",
            [{"code": "vendor_new", "message": "m", "blocking": False}],
        )
    )

    # Act
    detail = repo.get_by_id(1)

    # Assert
    assert detail.confirmation_source == "auto"
    assert detail.auto_confirm_reasons[0].code == "vendor_new"


@pytest.mark.unit
def test_get_all_filters_and_returns_confirmation_source():
    # Arrange
    repo, cursor = _repo(
        fetchall=[
            (1, "a.jpg", "done", "Lidl", "2026-09-30", "1.0", [], 3, False, 1, "auto"),
        ]
    )

    # Act
    items, total = repo.get_all(confirmation_source="auto")

    # Assert
    assert items[0].confirmation_source == "auto"
    assert total == 1
    sql, params = cursor.execute.call_args[0]
    assert "rs.confirmation_source = %s" in sql
    assert "auto" in params


@pytest.mark.unit
def test_mark_auto_confirm_reverted():
    # Arrange
    repo, cursor = _repo(cls=PromptAnalyticsRepository)

    # Act
    ok = repo.mark_auto_confirm_reverted(5)

    # Assert
    assert ok is True
    sql, params = cursor.execute.call_args[0]
    assert "auto_confirm_reverted = TRUE" in sql
    assert params == (5,)
