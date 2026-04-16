import pytest
from unittest.mock import MagicMock
from src.data import (
    EvaluationResult,
    EvaluationMetrics,
    EvaluationRunSummary,
    EvaluationRunListItem,
    EvaluationRunDetail,
    TransactionModel,
)
from src.repositories.evaluations import EvaluationsRepository


_UNSET = object()


class ConcreteEvaluations(EvaluationsRepository):
    """Minimal concrete subclass for testing the abstract base class."""
    pass


def make_repo(fetchone_return=_UNSET, fetchall_return=None):
    """Build an EvaluationsRepository backed by mock DB objects."""
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cursor)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_return is not _UNSET:
        cursor.fetchone.return_value = fetchone_return
    cursor.fetchall.return_value = fetchall_return or []
    repo = ConcreteEvaluations.__new__(ConcreteEvaluations)
    repo.conn = conn
    return repo, cursor


def _make_eval_result():
    """Helper to build a valid EvaluationResult."""
    return EvaluationResult(
        filename="receipt.jpg",
        success=True,
        error_message=None,
        metrics=EvaluationMetrics(
            processing_time_ms=500,
            fields_extracted=3,
            field_completeness=1.0,
            product_count=2,
            has_vendor=True,
            has_date=True,
            has_total=True,
            products_sum=99.99,
            extracted_total=99.99,
            total_difference=0.0,
            is_consistent=True,
        ),
        transaction=TransactionModel(
            vendor="Lidl",
            title="PARAGON",
            products=[],
            total=99.99,
            date="2026-01-15"
        ),
    )


# =============================================================================
# Tests for create_run
# =============================================================================

@pytest.mark.unit
def test_create_run_happy_path():
    # Arrange — INSERT RETURNING id returns 42
    repo, cursor = make_repo(fetchone_return=(42,))

    # Act
    result = repo.create_run(model_used="gpt-5.4", config={"max_tokens": 500})

    # Assert
    assert result == 42
    repo.conn.commit.assert_called_once()
    executed_sql = cursor.execute.call_args_list[0].args[0]
    assert "INSERT INTO evaluation_runs" in executed_sql
    assert "RETURNING id" in executed_sql


@pytest.mark.unit
def test_create_run_no_config():
    # Arrange — INSERT with None config
    repo, cursor = make_repo(fetchone_return=(99,))

    # Act
    result = repo.create_run(model_used="gpt-5.0")

    # Assert
    assert result == 99
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_create_run_no_connection():
    # Arrange — conn is None
    repo = ConcreteEvaluations.__new__(ConcreteEvaluations)
    repo.conn = None

    # Act
    result = repo.create_run(model_used="gpt-5.4")

    # Assert
    assert result == -1


@pytest.mark.unit
def test_create_run_db_error_rollback():
    # Arrange — cursor.execute raises exception
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    result = repo.create_run(model_used="gpt-5.4")

    # Assert
    assert result == -1
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


# =============================================================================
# Tests for add_result
# =============================================================================

@pytest.mark.unit
def test_add_result_happy_path():
    # Arrange
    repo, cursor = make_repo()
    result = _make_eval_result()

    # Act
    success = repo.add_result(run_id=1, result=result)

    # Assert
    assert success is True
    repo.conn.commit.assert_called_once()
    executed_sql = cursor.execute.call_args_list[0].args[0]
    assert "INSERT INTO evaluation_results" in executed_sql


@pytest.mark.unit
def test_add_result_no_metrics():
    # Arrange — result with no metrics
    repo, cursor = make_repo()
    result = EvaluationResult(
        filename="failed.jpg",
        success=False,
        error_message="OCR failed",
        metrics=None,
        transaction=None,
    )

    # Act
    success = repo.add_result(run_id=1, result=result)

    # Assert
    assert success is True
    repo.conn.commit.assert_called_once()


@pytest.mark.unit
def test_add_result_no_connection():
    # Arrange
    repo = ConcreteEvaluations.__new__(ConcreteEvaluations)
    repo.conn = None
    result = _make_eval_result()

    # Act
    success = repo.add_result(run_id=1, result=result)

    # Assert
    assert success is False


@pytest.mark.unit
def test_add_result_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("Constraint violation")
    result = _make_eval_result()

    # Act
    success = repo.add_result(run_id=1, result=result)

    # Assert
    assert success is False
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


# =============================================================================
# Tests for update_run_summary
# =============================================================================

@pytest.mark.unit
def test_update_run_summary_happy_path():
    # Arrange
    repo, cursor = make_repo()
    summary = MagicMock()
    summary.total_files = 10
    summary.successful = 9
    summary.failed = 1
    summary.success_rate = 0.9
    summary.avg_processing_time_ms = 300.0
    summary.avg_field_completeness = 0.95
    summary.avg_consistency_rate = 0.98

    # Act
    success = repo.update_run_summary(run_id=42, summary=summary)

    # Assert
    assert success is True
    repo.conn.commit.assert_called_once()
    executed_sql = cursor.execute.call_args_list[0].args[0]
    assert "UPDATE evaluation_runs" in executed_sql
    assert "avg_field_completeness" in executed_sql
    assert "avg_consistency_rate" in executed_sql


@pytest.mark.unit
def test_update_run_summary_no_connection():
    # Arrange
    repo = ConcreteEvaluations.__new__(ConcreteEvaluations)
    repo.conn = None
    summary = MagicMock()

    # Act
    success = repo.update_run_summary(run_id=42, summary=summary)

    # Assert
    assert success is False


@pytest.mark.unit
def test_update_run_summary_db_error_rollback():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("Column not found")
    summary = MagicMock()
    summary.total_files = 10
    summary.successful = 9
    summary.failed = 1
    summary.success_rate = 0.9
    summary.avg_processing_time_ms = 300.0
    summary.avg_field_completeness = 0.95
    summary.avg_consistency_rate = 0.98

    # Act
    success = repo.update_run_summary(run_id=42, summary=summary)

    # Assert
    assert success is False
    repo.conn.rollback.assert_called_once()
    repo.conn.commit.assert_not_called()


# =============================================================================
# Tests for get_all_runs
# =============================================================================

@pytest.mark.unit
def test_get_all_runs_happy_path():
    # Arrange — one run row
    repo, cursor = make_repo(
        fetchall_return=[
            (
                1,  # id
                "2026-04-16 10:30:00",  # run_timestamp
                "gpt-5.4",  # model_used
                10,  # total_files
                9,  # successful
                1,  # failed
                0.9,  # success_rate
                300.0,  # avg_processing_time_ms
                0.95,  # avg_field_completeness
                0.98,  # avg_consistency_rate
                {"max_tokens": 500},  # config
                1,  # total_count (over window function)
            )
        ]
    )

    # Act
    items, total = repo.get_all_runs(limit=50, offset=0)

    # Assert
    assert len(items) == 1
    assert total == 1
    assert isinstance(items[0], EvaluationRunListItem)
    assert items[0].id == 1
    assert items[0].model_used == "gpt-5.4"
    assert items[0].success_rate == 0.9


@pytest.mark.unit
def test_get_all_runs_with_sorting():
    # Arrange — test sorting parameter is used
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    repo.get_all_runs(limit=50, offset=0, sort_by="success_rate", sort_dir="asc")

    # Assert
    executed_sql = cursor.execute.call_args_list[0].args[0]
    assert "ORDER BY success_rate ASC" in executed_sql


@pytest.mark.unit
def test_get_all_runs_no_connection():
    # Arrange
    repo = ConcreteEvaluations.__new__(ConcreteEvaluations)
    repo.conn = None

    # Act
    items, total = repo.get_all_runs()

    # Assert
    assert items == []
    assert total == 0


@pytest.mark.unit
def test_get_all_runs_db_error_returns_empty():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("Query error")

    # Act
    items, total = repo.get_all_runs()

    # Assert
    assert items == []
    assert total == 0


@pytest.mark.unit
def test_get_all_runs_empty_result():
    # Arrange — no rows returned
    repo, cursor = make_repo(fetchall_return=[])

    # Act
    items, total = repo.get_all_runs()

    # Assert
    assert items == []
    assert total == 0


# =============================================================================
# Tests for get_run_with_results
# =============================================================================

@pytest.mark.unit
def test_get_run_with_results_happy_path():
    # Arrange — one run, two results
    repo, cursor = make_repo()
    run_row = (
        42,  # id
        "2026-04-16 10:30:00",  # run_timestamp
        "gpt-5.4",  # model_used
        2,  # total_files
        2,  # successful
        0,  # failed
        1.0,  # success_rate
        400.0,  # avg_processing_time_ms
        0.95,  # avg_field_completeness
        0.98,  # avg_consistency_rate
        {"max_tokens": 500},  # config
    )
    result_rows = [
        (
            "receipt1.jpg",  # filename
            True,  # success
            None,  # error_message
            500,  # processing_time_ms
            3,  # fields_extracted
            1.0,  # field_completeness
            2,  # product_count
            True,  # has_vendor
            True,  # has_date
            True,  # has_total
            99.99,  # products_sum
            99.99,  # extracted_total
            0.0,  # total_difference
            True,  # is_consistent
            {"vendor": "Lidl", "title": "PARAGON", "products": [], "total": 99.99, "date": "2026-01-15"},  # result (transaction JSON)
        ),
        (
            "receipt2.jpg",
            True,
            None,
            450,
            3,
            1.0,
            2,
            True,
            True,
            True,
            99.99,
            99.99,
            0.0,
            True,
            {"vendor": "Carrefour", "title": "PARAGON", "products": [], "total": 99.99, "date": "2026-01-16"},
        ),
    ]
    cursor.fetchone.return_value = run_row
    cursor.fetchall.return_value = result_rows

    # Act
    detail = repo.get_run_with_results(run_id=42)

    # Assert
    assert detail is not None
    assert isinstance(detail, EvaluationRunDetail)
    assert detail.id == 42
    assert detail.total_files == 2
    assert len(detail.results) == 2
    assert detail.results[0].filename == "receipt1.jpg"
    assert detail.results[0].success is True
    assert detail.results[0].metrics is not None
    assert detail.results[0].transaction is not None
    assert detail.results[0].transaction.vendor == "Lidl"


@pytest.mark.unit
def test_get_run_with_results_run_not_found():
    # Arrange — fetchone returns None for run
    repo, cursor = make_repo(fetchone_return=None)

    # Act
    detail = repo.get_run_with_results(run_id=999)

    # Assert
    assert detail is None


@pytest.mark.unit
def test_get_run_with_results_no_connection():
    # Arrange
    repo = ConcreteEvaluations.__new__(ConcreteEvaluations)
    repo.conn = None

    # Act
    detail = repo.get_run_with_results(run_id=42)

    # Assert
    assert detail is None


@pytest.mark.unit
def test_get_run_with_results_db_error_returns_none():
    # Arrange
    repo, cursor = make_repo()
    cursor.execute.side_effect = Exception("DB error")

    # Act
    detail = repo.get_run_with_results(run_id=42)

    # Assert
    assert detail is None


@pytest.mark.unit
def test_get_run_with_results_failed_result():
    # Arrange — result with success=False
    repo, cursor = make_repo()
    run_row = (
        1, "2026-04-16 10:30:00", "gpt-5.4", 1, 0, 1, 0.0, 0.0, 0.0, 0.0, None,
    )
    result_rows = [
        (
            "failed.jpg",
            False,  # success=False
            "OCR failed",
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        ),
    ]
    cursor.fetchone.return_value = run_row
    cursor.fetchall.return_value = result_rows

    # Act
    detail = repo.get_run_with_results(run_id=1)

    # Assert
    assert detail is not None
    assert len(detail.results) == 1
    assert detail.results[0].success is False
    assert detail.results[0].error_message == "OCR failed"
    assert detail.results[0].metrics is None


# =============================================================================
# Tests for dispose
# =============================================================================

@pytest.mark.unit
def test_dispose():
    # Arrange
    repo = ConcreteEvaluations.__new__(ConcreteEvaluations)
    repo.conn = MagicMock()

    # Act
    repo.dispose()

    # Assert — dispose should complete without error (it's a no-op)
    assert True
