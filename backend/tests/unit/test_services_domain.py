import datetime
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from src.data import (
    CreateFinancialGoalRequest,
    EvaluationMetrics,
    EvaluationResult,
    GroundTruthEntry,
    ProductItem,
    TransactionModel,
    UpdateFinancialGoalRequest,
)
from src.services.budget_analysis import BudgetAnalysisService
from src.services.budget_goals import BudgetGoalsService
from src.services.evaluation import EvaluationService
from src.services.ground_truth import GroundTruthService


def _make_transaction(
    vendor: str = "Biedronka",
    total: float = 0.0,
    date: str = "2024-01-01",
    products: list | None = None,
) -> TransactionModel:
    return TransactionModel(
        vendor=vendor,
        title="PARAGON FISKALNY",
        products=products or [],
        total=total,
        date=date,
    )


@pytest.mark.unit
class TestBudgetAnalysisService:
    def _make_service(self) -> tuple[BudgetAnalysisService, MagicMock]:
        mock_repo = MagicMock()
        mock_cats_repo = MagicMock()
        return BudgetAnalysisService(budget_analysis_repo=mock_repo, categories_repo=mock_cats_repo), mock_repo

    def test_get_monthly_breakdown_calls_repo(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.get_monthly_category_breakdown.return_value = []
        mock_repo.get_monthly_totals.return_value = {
            "expenses_pln": 3000.0,
            "income_pln": 5000.0,
            "prev_expenses_pln": 2800.0,
        }

        # Act
        result = svc.get_monthly_breakdown(2024, 1)

        # Assert
        mock_repo.get_monthly_category_breakdown.assert_called_once_with(2024, 1)
        assert result.total_income_pln == 5000.0
        assert result.surplus_pln == 2000.0

    def test_check_affordability_green_verdict(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.get_current_month_income_and_expenses.return_value = {
            "income_pln": 5000.0,
            "expenses_pln": 2000.0,
            "upcoming_recurring_sum_30d": 100.0,
        }

        # Act — 500 PLN is easily within available funds
        result = svc.check_affordability(500.0, None, 0.0)

        # Assert
        assert result.verdict == "green"
        assert result.amount_pln == 500.0


@pytest.mark.unit
class TestBudgetGoalsService:
    def _make_service(self) -> tuple[BudgetGoalsService, MagicMock, MagicMock]:
        mock_goals_repo = MagicMock()
        mock_analysis_repo = MagicMock()
        return (
            BudgetGoalsService(
                budget_goals_repo=mock_goals_repo,
                budget_analysis_repo=mock_analysis_repo,
            ),
            mock_goals_repo,
            mock_analysis_repo,
        )

    def test_get_monthly_surplus_calculates_correctly(self):
        # Arrange
        svc, mock_goals_repo, mock_analysis_repo = self._make_service()
        mock_analysis_repo.get_rolling_3month_averages.return_value = {
            "avg_income": 5000.0,
            "avg_expenses": 3000.0,
        }
        mock_analysis_repo.get_current_month_income_and_expenses.return_value = {
            "income_pln": 5000.0,
            "expenses_pln": 3000.0,
        }
        mock_goals_repo.get_active_goal_allocations_total.return_value = 500.0

        # Act
        result = svc.get_monthly_surplus()

        # Assert
        assert result.current_month_surplus_pln == 2000.0
        assert result.unallocated_surplus_pln == 1500.0

    def test_create_goal_calls_repo(self):
        # Arrange
        svc, mock_goals_repo, _ = self._make_service()
        mock_goals_repo.create_goal.return_value = {
            "id": 1,
            "name": "Wakacje",
            "target_amount": "5000.00",
            "priority_rank": 1,
            "monthly_allocation_amount": "500.00",
            "accumulated_progress": "0.00",
            "is_active": True,
            "target_date": None,
            "created_at": datetime.datetime.now(),
        }
        req = CreateFinancialGoalRequest(
            name="Wakacje",
            target_amount_pln=5000.0,
            priority_rank=1,
            monthly_allocation_amount_pln=500.0,
        )

        # Act
        result = svc.create_goal(req)

        # Assert
        mock_goals_repo.create_goal.assert_called_once()
        assert result.id == 1


@pytest.mark.unit
class TestGroundTruthService:
    def _make_service(self):
        mock_gt_repo = MagicMock()
        mock_minio = MagicMock()
        mock_preprocessing = MagicMock()
        mock_ocr = MagicMock()
        svc = GroundTruthService(
            ground_truth_repository=mock_gt_repo,
            minio_service=mock_minio,
            preprocessing_service=mock_preprocessing,
            ocr_service=mock_ocr,
        )
        return svc, mock_gt_repo

    def test_create_from_confirmed_receipt_stores_entry(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_filename.return_value = None
        mock_gt_repo.create.return_value = 1
        transaction = _make_transaction()

        # Act
        svc.create_from_confirmed_receipt("receipt.jpg", "key/receipt.jpg", transaction)

        # Assert
        mock_gt_repo.create.assert_called_once()

    def test_create_from_confirmed_receipt_skips_if_no_key(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        transaction = _make_transaction()

        # Act
        svc.create_from_confirmed_receipt("receipt.jpg", None, transaction)

        # Assert — repo.create must NOT be called when minio_object_key is None
        mock_gt_repo.create.assert_not_called()


@pytest.mark.unit
class TestEvaluationServiceCalculateMetrics:
    def _make_service(self) -> EvaluationService:
        return EvaluationService(
            evaluations_repository=MagicMock(),
            ground_truth_repository=MagicMock(),
            minio_service=MagicMock(),
            preprocessing_service=MagicMock(),
            ocr_service=MagicMock(),
        )

    def test_all_fields_match_ground_truth(self):
        # Arrange
        svc = self._make_service()
        txn = _make_transaction(vendor="Biedronka", total=29.99, date="2024-03-15")
        gt = _make_transaction(vendor="Biedronka", total=29.99, date="2024-03-15")

        # Act
        metrics = svc.calculate_metrics(txn, 100, ground_truth=gt)

        # Assert
        assert metrics.vendor_correct is True
        assert metrics.date_correct is True
        assert metrics.total_correct is True
        assert metrics.products_accuracy == 1.0

    def test_ground_truth_none_returns_none_comparison_fields(self):
        # Arrange
        svc = self._make_service()
        txn = _make_transaction()

        # Act
        metrics = svc.calculate_metrics(txn, 50, ground_truth=None)

        # Assert
        assert metrics.vendor_correct is None
        assert metrics.date_correct is None
        assert metrics.total_correct is None
        assert metrics.products_accuracy is None

    def test_products_accuracy_both_empty(self):
        # Arrange
        svc = self._make_service()
        txn = _make_transaction(products=[])
        gt = _make_transaction(products=[])

        # Act
        metrics = svc.calculate_metrics(txn, 50, ground_truth=gt)

        # Assert
        assert metrics.products_accuracy == 1.0

    def test_total_zero_no_division_error(self):
        # Arrange
        svc = self._make_service()
        txn = _make_transaction(total=0.0)
        gt = _make_transaction(total=0.0)

        # Act — should not raise ZeroDivisionError
        metrics = svc.calculate_metrics(txn, 50, ground_truth=gt)

        # Assert
        assert metrics.total_accuracy == 1.0

    def test_products_accuracy_no_match(self):
        # Arrange
        svc = self._make_service()
        txn = _make_transaction(products=[])
        gt = TransactionModel(
            vendor="Biedronka",
            title="PARAGON FISKALNY",
            products=[ProductItem(name="Mleko", quantity=1, price=3.5)],
            total=3.5,
            date="2024-01-01",
        )

        # Act
        metrics = svc.calculate_metrics(txn, 50, ground_truth=gt)

        # Assert
        assert metrics.products_accuracy == 0.0


@pytest.mark.unit
class TestEvaluationServiceAsync:
    def _make_service(self):
        mock_eval_repo = MagicMock()
        mock_gt_repo = MagicMock()
        mock_minio = MagicMock()
        mock_preprocessing = MagicMock()
        mock_ocr = MagicMock()
        svc = EvaluationService(
            evaluations_repository=mock_eval_repo,
            ground_truth_repository=mock_gt_repo,
            minio_service=mock_minio,
            preprocessing_service=mock_preprocessing,
            ocr_service=mock_ocr,
        )
        return svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr

    async def test_run_evaluation_async_empty_ground_truth(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, _, _, mock_ocr = self._make_service()
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test"
        mock_eval_repo.create_run.return_value = 1
        mock_gt_repo.get_all.return_value = ([], 0)

        # Act
        result = await svc.run_evaluation_async()

        # Assert
        assert result.total_files == 0
        mock_eval_repo.add_result.assert_not_called()

    async def test_run_evaluation_async_single_entry(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr = self._make_service()

        entry = GroundTruthEntry(
            id=1,
            filename="receipt.jpg",
            minio_object_key="gt/receipt.jpg",
            ground_truth=_make_transaction(vendor="Lidl", total=10.0),
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test prompt"
        mock_eval_repo.create_run.return_value = 42
        mock_gt_repo.get_all.return_value = ([entry], 1)
        mock_minio.get_temp_file.return_value = "/tmp/fake_path.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/fake_path.jpg"
        mock_ocr.process_image_async = AsyncMock(
            return_value={
                "vendor": "Lidl",
                "title": "PARAGON FISKALNY",
                "products": [],
                "total": 10.0,
                "date": "2024-01-01",
            }
        )

        # Act
        result = await svc.run_evaluation_async()

        # Assert
        assert result.total_files == 1
        assert result.successful == 1
        mock_eval_repo.add_result.assert_called_once()


def _make_goal_row(
    id: int = 1,
    name: str = "Wakacje",
    target: str = "5000.00",
    progress: str = "0.00",
    alloc: str = "500.00",
    is_active: bool = True,
) -> dict:
    return {
        "id": id,
        "name": name,
        "target_amount": target,
        "accumulated_progress": progress,
        "monthly_allocation_amount": alloc,
        "is_active": is_active,
        "priority_rank": 1,
        "target_date": None,
        "created_at": datetime.datetime(2024, 1, 1),
    }


@pytest.mark.unit
class TestBudgetGoalsServiceExtended:
    def _make_service(self):
        mock_goals_repo = MagicMock()
        mock_analysis_repo = MagicMock()
        svc = BudgetGoalsService(
            budget_goals_repo=mock_goals_repo,
            budget_analysis_repo=mock_analysis_repo,
        )
        return svc, mock_goals_repo, mock_analysis_repo

    def test_get_goals_returns_enriched_list(self):
        # Arrange
        svc, mock_goals_repo, _ = self._make_service()
        mock_goals_repo.get_all_goals.return_value = [_make_goal_row()]

        # Act
        result = svc.get_goals()

        # Assert
        assert len(result) == 1
        assert result[0].name == "Wakacje"

    def test_enrich_goal_already_completed(self):
        # Arrange — progress == target → remaining == 0 → months_to_completion = 0
        svc, mock_goals_repo, _ = self._make_service()
        mock_goals_repo.get_all_goals.return_value = [
            _make_goal_row(progress="5000.00")
        ]

        # Act
        result = svc.get_goals()

        # Assert
        assert result[0].months_to_completion == 0

    def test_enrich_goal_target_date_is_date_object(self):
        # Arrange
        svc, mock_goals_repo, _ = self._make_service()
        row = _make_goal_row()
        row["target_date"] = datetime.date(2025, 12, 31)
        mock_goals_repo.get_all_goals.return_value = [row]

        # Act
        result = svc.get_goals()

        # Assert — datetime.date converted to ISO string
        assert result[0].target_date == "2025-12-31"

    def test_create_goal_raises_when_repo_returns_none(self):
        # Arrange
        svc, mock_goals_repo, _ = self._make_service()
        mock_goals_repo.create_goal.return_value = None
        req = CreateFinancialGoalRequest(
            name="Laptop",
            target_amount_pln=3000.0,
            priority_rank=1,
            monthly_allocation_amount_pln=300.0,
        )

        # Act / Assert
        with pytest.raises(ValueError):
            svc.create_goal(req)

    def test_update_goal_returns_none_when_repo_returns_none(self):
        # Arrange
        svc, mock_goals_repo, _ = self._make_service()
        mock_goals_repo.update_goal.return_value = None
        req = UpdateFinancialGoalRequest(name="Updated")

        # Act
        result = svc.update_goal(1, req)

        # Assert
        assert result is None

    def test_update_goal_returns_enriched(self):
        # Arrange
        svc, mock_goals_repo, _ = self._make_service()
        mock_goals_repo.update_goal.return_value = _make_goal_row(name="Updated")
        req = UpdateFinancialGoalRequest(name="Updated")

        # Act
        result = svc.update_goal(1, req)

        # Assert
        assert result is not None
        assert result.name == "Updated"

    def test_delete_goal_delegates(self):
        # Arrange
        svc, mock_goals_repo, _ = self._make_service()
        mock_goals_repo.soft_delete_goal.return_value = True

        # Act
        result = svc.delete_goal(1)

        # Assert
        assert result is True
        mock_goals_repo.soft_delete_goal.assert_called_once_with(1)


@pytest.mark.unit
class TestBudgetAnalysisServiceExtended:
    def _make_service(self):
        mock_repo = MagicMock()
        mock_cats_repo = MagicMock()
        return BudgetAnalysisService(budget_analysis_repo=mock_repo, categories_repo=mock_cats_repo), mock_repo

    def test_get_monthly_breakdown_with_category_rows(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.get_monthly_category_breakdown.return_value = [
            {"category_id": 1, "category_name": "Jedzenie", "classification": "essential",
             "total_pln": "600.00", "prev_month_pln": "500.00"},
        ]
        mock_repo.get_monthly_totals.return_value = {
            "expenses_pln": 1000.0,
            "income_pln": 5000.0,
            "prev_expenses_pln": 900.0,
        }

        # Act
        result = svc.get_monthly_breakdown(2024, 1)

        # Assert
        assert len(result.categories) == 1
        assert result.categories[0].pct_of_total == pytest.approx(60.0, abs=0.1)
        assert result.categories[0].change_pct == pytest.approx(20.0, abs=0.1)

    def test_seed_and_get_classifications(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.get_all_category_ids.return_value = [
            {"id": 1, "name": "Jedzenie"},
            {"id": 2, "name": "Transport"},
        ]
        mock_repo.get_classified_category_ids.return_value = {1}
        mock_repo.get_all_classifications.return_value = [
            {"category_id": 1, "category_name": "Jedzenie", "classification": "essential", "is_user_override": False},
            {"category_id": 2, "category_name": "Transport", "classification": "essential", "is_user_override": False},
        ]

        # Act
        result = svc.seed_and_get_classifications()

        # Assert — only category 2 was missing, so upsert called once
        mock_repo.upsert_classification.assert_called_once()
        assert len(result) == 2

    def test_update_category_classification_success(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.upsert_classification.return_value = True
        mock_repo.get_classification_by_category.return_value = {
            "category_id": 1,
            "category_name": "Jedzenie",
            "classification": "discretionary",
            "is_user_override": True,
        }

        # Act
        result = svc.update_category_classification(1, "discretionary")

        # Assert
        assert result.classification == "discretionary"

    def test_update_category_classification_raises_when_upsert_fails(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.upsert_classification.return_value = False

        # Act / Assert
        with pytest.raises(ValueError):
            svc.update_category_classification(99, "discretionary")

    def test_get_financial_focus_none_returns_default(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.get_financial_focus.return_value = None

        # Act
        result = svc.get_financial_focus()

        # Assert
        assert result.label == ""
        assert result.is_active is False

    def test_set_financial_focus_raises_when_repo_fails(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.set_financial_focus.return_value = None

        # Act / Assert
        with pytest.raises(ValueError):
            svc.set_financial_focus("Oszczędności", None)

    def test_get_recurring_expenses_converts_rows(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.get_recurring_expenses.return_value = [
            {
                "vendor_name": "Netflix",
                "category_name": "Rozrywka",
                "frequency": "monthly",
                "avg_amount_pln": 50.0,
                "last_occurrence_date": "2024-01-01",
                "next_expected_date": "2024-02-01",
                "amount_min_pln": 49.0,
                "amount_max_pln": 51.0,
                "occurrence_count": 6,
            }
        ]

        # Act
        result = svc.get_recurring_expenses()

        # Assert
        assert len(result) == 1
        assert result[0].vendor_name == "Netflix"

    def test_get_cyclical_alerts_converts_rows(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.get_cyclical_alerts.return_value = [
            {
                "vendor_name": "Allegro",
                "category_name": "Zakupy",
                "next_expected_date": "2024-02-15",
                "days_until": 7,
                "expected_amount_pln": 120.0,
                "amount_range_pln": "100–140",
            }
        ]

        # Act
        result = svc.get_cyclical_alerts()

        # Assert
        assert len(result) == 1
        assert result[0].vendor_name == "Allegro"

    def test_check_affordability_yellow_verdict(self):
        # Arrange — amount > freely_available but <= available_this_month
        svc, mock_repo = self._make_service()
        mock_repo.get_current_month_income_and_expenses.return_value = {
            "income_pln": 5000.0,
            "expenses_pln": 2000.0,
            "upcoming_recurring_sum_30d": 2500.0,  # big upcoming obligations
        }

        # Act — 700 exceeds freely_available (5000-2000-2500=500) but within available (3000)
        result = svc.check_affordability(700.0, None, 0.0)

        # Assert
        assert result.verdict == "yellow"

    def test_check_affordability_red_verdict(self):
        # Arrange — amount > available_this_month
        svc, mock_repo = self._make_service()
        mock_repo.get_current_month_income_and_expenses.return_value = {
            "income_pln": 2000.0,
            "expenses_pln": 1800.0,
            "upcoming_recurring_sum_30d": 0.0,
        }

        # Act — 500 > available (200)
        result = svc.check_affordability(500.0, None, 0.0)

        # Assert
        assert result.verdict == "red"

    def test_update_category_classification_raises_when_row_is_none(self):
        # Arrange — upsert succeeds but get returns None
        svc, mock_repo = self._make_service()
        mock_repo.upsert_classification.return_value = True
        mock_repo.get_classification_by_category.return_value = None

        # Act / Assert
        with pytest.raises(ValueError):
            svc.update_category_classification(1, "discretionary")

    def test_set_financial_focus_returns_response(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.set_financial_focus.return_value = {
            "id": 1, "label": "Oszczędności", "description": None, "is_active": True
        }

        # Act
        result = svc.set_financial_focus("Oszczędności", None)

        # Assert
        assert result.label == "Oszczędności"

    def test_get_emergency_advice_fully_coverable(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.get_discretionary_category_averages.return_value = [
            {"category_name": "Restauracje", "avg_monthly_spend_pln": "300.00"},
            {"category_name": "Rozrywka", "avg_monthly_spend_pln": "200.00"},
        ]
        active_goals = [
            {"id": 1, "name": "Wakacje", "monthly_allocation_amount": "500.00"}
        ]

        # Act
        result = svc.get_emergency_advice(400.0, active_goals)

        # Assert
        assert result.fully_coverable_by_cuts is True
        assert len(result.discretionary_cuts) == 2
        assert len(result.goal_impacts) == 1

    def test_get_emergency_advice_not_fully_coverable(self):
        # Arrange — total cuttable < amount_pln
        svc, mock_repo = self._make_service()
        mock_repo.get_discretionary_category_averages.return_value = [
            {"category_name": "Restauracje", "avg_monthly_spend_pln": "100.00"},
        ]

        # Act
        result = svc.get_emergency_advice(5000.0, [])

        # Assert
        assert result.fully_coverable_by_cuts is False

    def test_check_affordability_appends_focus_label(self):
        # Arrange
        svc, mock_repo = self._make_service()
        mock_repo.get_current_month_income_and_expenses.return_value = {
            "income_pln": 5000.0,
            "expenses_pln": 1000.0,
            "upcoming_recurring_sum_30d": 0.0,
        }

        # Act
        result = svc.check_affordability(100.0, "Oszczędności na dom", 0.0)

        # Assert — narrative should mention the focus label
        assert "Oszczędności na dom" in result.narrative


@pytest.mark.unit
class TestGroundTruthServiceExtended:
    def _make_service(self):
        mock_gt_repo = MagicMock()
        svc = GroundTruthService(
            ground_truth_repository=mock_gt_repo,
            minio_service=MagicMock(),
            preprocessing_service=MagicMock(),
            ocr_service=MagicMock(),
        )
        return svc, mock_gt_repo

    def _make_entry(self, id: int = 1, filename: str = "receipt.jpg") -> GroundTruthEntry:
        return GroundTruthEntry(
            id=id,
            filename=filename,
            minio_object_key="gt/receipt.jpg",
            ground_truth=_make_transaction(),
            created_at=datetime.datetime(2024, 1, 1),
            updated_at=datetime.datetime(2024, 1, 1),
        )

    def test_update_returns_response(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_id.return_value = self._make_entry()
        mock_gt_repo.update.return_value = True
        tx = _make_transaction()

        # Act
        result = svc.update(1, tx)

        # Assert
        assert result is not None
        assert result.id == 1

    def test_update_returns_none_when_not_found(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_id.return_value = None

        # Act
        result = svc.update(99, _make_transaction())

        # Assert
        assert result is None

    def test_get_returns_response(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_id.return_value = self._make_entry()

        # Act
        result = svc.get(1)

        # Assert
        assert result is not None
        assert result.filename == "receipt.jpg"

    def test_get_returns_none_when_not_found(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_id.return_value = None

        # Act
        result = svc.get(99)

        # Assert
        assert result is None

    def test_list_returns_responses(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_all.return_value = ([self._make_entry()], 1)

        # Act
        entries, total = svc.list()

        # Assert
        assert total == 1
        assert len(entries) == 1
        assert entries[0].id == 1

    def test_create_from_confirmed_receipt_already_exists(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_filename.return_value = self._make_entry()

        # Act
        svc.create_from_confirmed_receipt("receipt.jpg", "key/receipt.jpg", _make_transaction())

        # Assert — create must NOT be called when entry already exists
        mock_gt_repo.create.assert_not_called()

    def test_create_from_confirmed_receipt_failure_path(self):
        # Arrange — create returns -1 (failure code)
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_filename.return_value = None
        mock_gt_repo.create.return_value = -1

        # Act — should not raise
        svc.create_from_confirmed_receipt("receipt.jpg", "key/receipt.jpg", _make_transaction())

        # Assert
        mock_gt_repo.create.assert_called_once()

    def test_create_happy_path(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_filename.return_value = None
        mock_gt_repo.create.return_value = 7
        mock_gt_repo.get_by_id.return_value = self._make_entry(id=7, filename="new.jpg")
        svc.minio_service.get_temp_file.return_value = "/tmp/new.jpg"
        svc.preprocessing_service.preprocess_image.return_value = "/tmp/new.jpg"
        svc.ocr_service.process_image.return_value = {
            "vendor": "Biedronka", "title": "PARAGON FISKALNY",
            "products": [], "total": 0.0, "date": "2024-01-01",
        }

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc.create("new.jpg", b"fake image data")

        # Assert
        assert svc.minio_service.upload_image.call_count == 1
        upload_args = svc.minio_service.upload_image.call_args[0]
        assert upload_args[0] == b"fake image data"
        assert "new.jpg" in upload_args[1]
        mock_gt_repo.create.assert_called_once()
        assert result.id == 7
        assert result.filename == "new.jpg"

    def test_create_raises_on_duplicate_filename(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_filename.return_value = self._make_entry()

        # Act / Assert
        with pytest.raises(ValueError, match="already exists"):
            svc.create("receipt.jpg", b"data")

    def test_update_returns_none_when_update_fails(self):
        # Arrange
        svc, mock_gt_repo = self._make_service()
        mock_gt_repo.get_by_id.return_value = self._make_entry()
        mock_gt_repo.update.return_value = False

        # Act
        result = svc.update(1, _make_transaction())

        # Assert
        assert result is None


@pytest.mark.unit
class TestEvaluationServiceSync:
    def _make_service(self):
        mock_eval_repo = MagicMock()
        mock_gt_repo = MagicMock()
        mock_minio = MagicMock()
        mock_preprocessing = MagicMock()
        mock_ocr = MagicMock()
        svc = EvaluationService(
            evaluations_repository=mock_eval_repo,
            ground_truth_repository=mock_gt_repo,
            minio_service=mock_minio,
            preprocessing_service=mock_preprocessing,
            ocr_service=mock_ocr,
        )
        return svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr

    def _make_entry(self, id: int = 1, filename: str = "receipt.jpg") -> GroundTruthEntry:
        return GroundTruthEntry(
            id=id,
            filename=filename,
            minio_object_key="gt/receipt.jpg",
            ground_truth=_make_transaction(vendor="Lidl", total=10.0),
            created_at=datetime.datetime.now(),
            updated_at=datetime.datetime.now(),
        )

    def test_run_evaluation_empty_entries(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, _, _, mock_ocr = self._make_service()
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test"
        mock_eval_repo.create_run.return_value = 1
        mock_gt_repo.get_all.return_value = ([], 0)

        # Act
        result = svc.run_evaluation()

        # Assert
        assert result.total_files == 0
        mock_eval_repo.add_result.assert_not_called()

    def test_run_evaluation_happy_path(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test"
        mock_eval_repo.create_run.return_value = 42
        mock_gt_repo.get_all.return_value = ([self._make_entry()], 1)
        mock_minio.get_temp_file.return_value = "/tmp/fake.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/fake.jpg"
        mock_ocr.process_image.return_value = {
            "vendor": "Lidl", "title": "PARAGON FISKALNY",
            "products": [], "total": 10.0, "date": "2024-01-01",
        }

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc.run_evaluation()

        # Assert
        assert result.total_files == 1
        assert result.successful == 1
        mock_eval_repo.add_result.assert_called_once()
        mock_eval_repo.update_run_summary.assert_called_once()

    def test_run_evaluation_with_progress_callback(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test"
        mock_eval_repo.create_run.return_value = 1
        mock_gt_repo.get_all.return_value = ([self._make_entry()], 1)
        mock_minio.get_temp_file.return_value = "/tmp/fake.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/fake.jpg"
        mock_ocr.process_image.return_value = {
            "vendor": "Lidl", "title": "PARAGON FISKALNY",
            "products": [], "total": 10.0, "date": "2024-01-01",
        }
        progress_calls = []

        # Act
        with patch("os.path.exists", return_value=False):
            svc.run_evaluation(on_progress=lambda **kw: progress_calls.append(kw))

        # Assert
        assert len(progress_calls) == 1
        assert progress_calls[0]["index"] == 1
        assert progress_calls[0]["filename"] == "receipt.jpg"

    def test_run_evaluation_with_entry_ids(self):
        # Arrange
        svc, mock_eval_repo, mock_gt_repo, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_ocr.model = "gpt-5.2"
        mock_ocr.prompt = "test"
        mock_eval_repo.create_run.return_value = 1
        mock_gt_repo.get_by_ids.return_value = [self._make_entry(id=5)]
        mock_minio.get_temp_file.return_value = "/tmp/fake.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/fake.jpg"
        mock_ocr.process_image.return_value = {
            "vendor": "Lidl", "title": "PARAGON FISKALNY",
            "products": [], "total": 10.0, "date": "2024-01-01",
        }

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc.run_evaluation(entry_ids=[5])

        # Assert
        mock_gt_repo.get_by_ids.assert_called_once_with([5])
        mock_gt_repo.get_all.assert_not_called()
        assert result.total_files == 1

    def test_evaluate_entry_happy_path(self):
        # Arrange
        svc, _, _, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_minio.get_temp_file.return_value = "/tmp/fake.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/fake.jpg"
        mock_ocr.process_image.return_value = {
            "vendor": "Lidl", "title": "PARAGON FISKALNY",
            "products": [], "total": 10.0, "date": "2024-01-01",
        }

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc._evaluate_ground_truth_entry(self._make_entry())

        # Assert
        assert isinstance(result, EvaluationResult)
        assert result.success is True
        assert result.filename == "receipt.jpg"
        assert isinstance(result.metrics, EvaluationMetrics)

    def test_evaluate_entry_ocr_raises_returns_failure(self):
        # Arrange
        svc, _, _, mock_minio, mock_preprocessing, mock_ocr = self._make_service()
        mock_minio.get_temp_file.return_value = "/tmp/bad.jpg"
        mock_preprocessing.preprocess_image.return_value = "/tmp/bad.jpg"
        mock_ocr.process_image.side_effect = Exception("OCR failed")

        # Act
        with patch("os.path.exists", return_value=False):
            result = svc._evaluate_ground_truth_entry(self._make_entry(filename="bad.jpg"))

        # Assert
        assert result.success is False
        assert "OCR failed" in result.error_message


@pytest.mark.unit
class TestEvaluationServiceSummary:
    def _make_service(self) -> EvaluationService:
        return EvaluationService(
            evaluations_repository=MagicMock(),
            ground_truth_repository=MagicMock(),
            minio_service=MagicMock(),
            preprocessing_service=MagicMock(),
            ocr_service=MagicMock(),
        )

    def _make_successful_result(
        self,
        vendor_correct: bool = True,
        date_correct: bool = True,
        total_accuracy: float = 1.0,
        products_accuracy: float = 1.0,
    ) -> EvaluationResult:
        metrics = EvaluationMetrics(
            processing_time_ms=100,
            fields_extracted=5,
            field_completeness=1.0,
            product_count=0,
            has_vendor=True,
            has_date=True,
            has_total=True,
            products_sum=0.0,
            extracted_total=0.0,
            total_difference=0.0,
            is_consistent=True,
            vendor_correct=vendor_correct,
            date_correct=date_correct,
            total_correct=True,
            total_accuracy=total_accuracy,
            product_count_correct=True,
            products_accuracy=products_accuracy,
        )
        return EvaluationResult(
            filename="receipt.jpg",
            success=True,
            metrics=metrics,
            transaction=_make_transaction(),
        )

    def test_calculate_summary_with_ground_truth_metrics(self):
        # Arrange
        svc = self._make_service()
        results = [self._make_successful_result(vendor_correct=True, total_accuracy=0.95)]

        # Act
        summary = svc._calculate_summary(run_id=1, model_used="gpt-5.2", results=results)

        # Assert
        assert summary.avg_vendor_accuracy == 1.0
        assert summary.avg_date_accuracy == 1.0
        assert summary.avg_total_accuracy == 0.95
        assert summary.avg_products_accuracy == 1.0
        assert summary.successful == 1
        assert summary.failed == 0
        assert summary.avg_field_completeness == 1.0
        assert summary.avg_consistency_rate == 1.0

    def test_calculate_summary_vendor_incorrect(self):
        # Arrange
        svc = self._make_service()
        results = [self._make_successful_result(vendor_correct=False, total_accuracy=1.0)]

        # Act
        summary = svc._calculate_summary(run_id=1, model_used="gpt-5.2", results=results)

        # Assert
        assert summary.avg_vendor_accuracy == 0.0
        assert summary.avg_date_accuracy == 1.0
        assert summary.avg_total_accuracy == 1.0
        assert summary.avg_products_accuracy == 1.0

    def test_calculate_summary_no_successful_results(self):
        # Arrange
        svc = self._make_service()
        results = [
            EvaluationResult(filename="bad.jpg", success=False, error_message="OCR failed")
        ]

        # Act
        summary = svc._calculate_summary(run_id=1, model_used="gpt-5.2", results=results)

        # Assert
        assert summary.successful == 0
        assert summary.failed == 1
        assert summary.avg_vendor_accuracy is None
        assert summary.avg_date_accuracy is None
        assert summary.avg_field_completeness == 0.0
        assert summary.avg_consistency_rate == 0.0
        assert summary.avg_total_accuracy is None
        assert summary.avg_products_accuracy is None
