import json
import pytest
from unittest.mock import MagicMock, AsyncMock

from src.data import BankTransactionDetail, ProductItem, TransactionModel
from src.services.bank_categorization import BankCategorizationService, _normalize_counterparty
from src.services.budget_simulation import BudgetSimulationService
from src.services.categories import CategoriesService
from src.services.ocr import OCRService
from src.services.products import ProductsService
from src.services.vendors import VendorsService


_MINIMAL_TRANSACTION_DICT = {
    "vendor": "Biedronka",
    "title": "PARAGON FISKALNY",
    "products": [],
    "total": 0.0,
    "date": "2024-01-01",
}


def _make_sync_response(payload: dict) -> MagicMock:
    """Build a mock sync client.responses.create() return value."""
    tool_call = MagicMock()
    tool_call.type = "function_call"
    tool_call.arguments = json.dumps(payload)
    response = MagicMock()
    response.output = [tool_call]
    return response


def _make_async_response(payload: dict) -> MagicMock:
    """Same shape but returned by an AsyncMock."""
    tool_call = MagicMock()
    tool_call.type = "function_call"
    tool_call.arguments = json.dumps(payload)
    response = MagicMock()
    response.output = [tool_call]
    return response


@pytest.mark.unit
class TestOCRService:
    def test_process_image_happy_path(self, tmp_path):
        # Arrange — write fake bytes so _encode_image can open the file
        img_path = str(tmp_path / "receipt.jpg")
        (tmp_path / "receipt.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)

        mock_client = MagicMock()
        mock_client.responses.create.return_value = _make_sync_response(_MINIMAL_TRANSACTION_DICT)
        svc = OCRService(client=mock_client, async_client=MagicMock())

        # Act
        result = svc.process_image(img_path)

        # Assert
        assert result["vendor"] == "Biedronka"
        mock_client.responses.create.assert_called_once()

    async def test_process_image_async_happy_path(self, tmp_path):
        # Arrange
        img_path = str(tmp_path / "receipt.jpg")
        (tmp_path / "receipt.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)

        mock_async_client = MagicMock()
        mock_async_client.responses.create = AsyncMock(
            return_value=_make_async_response(_MINIMAL_TRANSACTION_DICT)
        )
        svc = OCRService(client=MagicMock(), async_client=mock_async_client)

        # Act
        result = await svc.process_image_async(img_path)

        # Assert
        assert result["vendor"] == "Biedronka"
        mock_async_client.responses.create.assert_called_once()

    def test_process_image_malformed_json_raises(self, tmp_path):
        # Arrange
        img_path = str(tmp_path / "receipt.jpg")
        (tmp_path / "receipt.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 10)

        tool_call = MagicMock()
        tool_call.type = "function_call"
        tool_call.arguments = "{not valid json"
        response = MagicMock()
        response.output = [tool_call]

        mock_client = MagicMock()
        mock_client.responses.create.return_value = response
        svc = OCRService(client=mock_client, async_client=MagicMock())

        # Act / Assert
        with pytest.raises(Exception):
            svc.process_image(img_path)

    def test_prompt_contains_lidl_discount_rules(self):
        # Arrange
        svc = OCRService(client=MagicMock(), async_client=MagicMock())

        # Assert — both concrete examples and the general guard are present
        assert "Lidl Plus kupon" in svc.prompt
        assert "Lidl Plus voucher" in svc.prompt
        assert "Taniej za 2" in svc.prompt
        assert "Never assign a positive price" in svc.prompt


@pytest.mark.unit
class TestCategoriesService:
    def _make_service(self) -> tuple[CategoriesService, MagicMock]:
        mock_db = MagicMock()
        mock_client = MagicMock()
        svc = CategoriesService(db_context=mock_db, client=mock_client)
        svc.categories = "category_id | category_name"
        return svc, mock_client

    def test_assign_candidates_happy_path(self):
        # Arrange
        svc, mock_client = self._make_service()
        payload = {
            "category_candidates": [
                {
                    "product_name": "Mleko",
                    "category_candidates": [
                        {"category_id": 1, "category_name": "Nabiał", "category_score": 0.9}
                    ],
                }
            ]
        }
        mock_client.responses.create.return_value = _make_sync_response(payload)
        transaction = TransactionModel(
            **_MINIMAL_TRANSACTION_DICT
            | {"products": [{"name": "Mleko", "quantity": 1, "price": 2.5, "unit_price": 2.5}]}
        )

        # Act
        result = svc.assign_category_candidates(transaction)

        # Assert
        assert isinstance(result, dict)
        mock_client.responses.create.assert_called_once()

    def test_assign_candidates_malformed_json_raises(self):
        # Arrange
        svc, mock_client = self._make_service()
        tool_call = MagicMock()
        tool_call.type = "function_call"
        tool_call.arguments = "{bad json"
        response = MagicMock()
        response.output = [tool_call]
        mock_client.responses.create.return_value = response
        transaction = TransactionModel(**_MINIMAL_TRANSACTION_DICT)

        # Act / Assert
        with pytest.raises(Exception):
            svc.assign_category_candidates(transaction)


@pytest.mark.unit
class TestBankCategorizationService:
    def _make_service(self) -> tuple[BankCategorizationService, MagicMock, MagicMock]:
        mock_db = MagicMock()
        mock_db.conn = None  # forces _build_context_section to return ""
        mock_client = MagicMock()
        mock_async_client = MagicMock()
        svc = BankCategorizationService(
            db_context=mock_db,
            client=mock_client,
            async_client=mock_async_client,
        )
        svc.categories_table = "category_id | category_name"
        return svc, mock_client, mock_async_client

    def _make_tx(self) -> BankTransactionDetail:
        return BankTransactionDetail(
            id=1,
            reference_number="REF001",
            booking_date="2024-01-15",
            amount=50.0,
            currency="PLN",
        )

    def test_assign_candidates_happy_path(self):
        # Arrange
        svc, mock_client, _ = self._make_service()
        payload = {
            "category_candidates": [
                {"category_id": 1, "category_name": "Spożywcze", "category_score": 0.95}
            ]
        }
        mock_client.responses.create.return_value = _make_sync_response(payload)
        tx = self._make_tx()

        # Act
        result = svc.assign_candidates(tx)

        # Assert
        assert isinstance(result, list)
        assert result[0]["category_id"] == 1
        mock_client.responses.create.assert_called_once()

    async def test_assign_candidates_async_happy_path(self):
        # Arrange
        import asyncio

        svc, _, mock_async_client = self._make_service()
        payload = {
            "category_candidates": [
                {"category_id": 2, "category_name": "Transport", "category_score": 0.8}
            ]
        }
        mock_async_client.responses.create = AsyncMock(
            return_value=_make_async_response(payload)
        )
        tx = self._make_tx()
        db_lock = asyncio.Lock()

        # Act
        result = await svc.assign_candidates_async(tx, db_lock)

        # Assert
        assert isinstance(result, list)
        assert result[0]["category_id"] == 2


@pytest.mark.unit
class TestProductsService:
    def test_process_products_happy_path(self):
        # Arrange
        mock_client = MagicMock()
        payload = {
            "products": [
                {"product_alternative_name": "MLEKO ŁACIĄTE 2%", "product_name": "Mleko"}
            ]
        }
        mock_client.responses.create.return_value = _make_sync_response(payload)
        svc = ProductsService(client=mock_client)
        products = [ProductItem(name="MLEKO ŁACIĄTE 2%", quantity=1, price=3.5)]

        # Act
        result = svc.process_products(products)

        # Assert
        assert result.products[0].product_name == "Mleko"
        mock_client.responses.create.assert_called_once()


@pytest.mark.unit
class TestVendorsService:
    def test_process_vendor_happy_path(self):
        # Arrange
        mock_client = MagicMock()
        payload = {
            "vendor_alternative_name": "ALDI Sp. z o.o.",
            "vendor_name": "Aldi",
        }
        mock_client.responses.create.return_value = _make_sync_response(payload)
        svc = VendorsService(client=mock_client)

        # Act
        result = svc.process_vendor("ALDI Sp. z o.o.")

        # Assert
        assert result.vendor_name == "Aldi"
        mock_client.responses.create.assert_called_once()


@pytest.mark.unit
class TestBudgetSimulationService:
    def _make_service(self):
        mock_analysis_repo = MagicMock()
        mock_goals_repo = MagicMock()
        mock_simulations_repo = MagicMock()
        mock_client = MagicMock()
        svc = BudgetSimulationService(
            budget_analysis_repo=mock_analysis_repo,
            budget_goals_repo=mock_goals_repo,
            budget_simulations_repo=mock_simulations_repo,
            openai_client=mock_client,
        )
        return svc, mock_analysis_repo, mock_goals_repo, mock_simulations_repo, mock_client

    def test_generate_ai_recommendations_insufficient_data(self):
        # Arrange
        svc, mock_analysis_repo, _, _, _ = self._make_service()
        mock_analysis_repo.count_distinct_months.return_value = 1

        # Act
        result = svc.generate_ai_recommendations()

        # Assert
        assert result.has_sufficient_data is False
        assert result.insights == []

    def test_run_projection_calls_repo_and_returns_12_months(self):
        # Arrange
        svc, mock_analysis_repo, mock_goals_repo, _, mock_client = self._make_service()
        mock_analysis_repo.get_rolling_3month_averages.return_value = {
            "avg_income": 5000.0,
            "avg_expenses": 3000.0,
        }
        mock_goals_repo.get_all_goals.return_value = []
        # Narrative LLM call fails gracefully — fallback narrative is used
        mock_client.chat.completions.create.side_effect = Exception("no api key in test")
        simulation_row = {
            "expense_amount": 500.0,
            "expense_type": "one_time",
            "expense_start_date": "2024-06-01",
            "expense_name": "Nowy laptop",
        }

        # Act
        result = svc.run_projection(simulation_row)

        # Assert
        mock_analysis_repo.get_rolling_3month_averages.assert_called_once()
        assert len(result.projection) == 12  # one_time → 12-month horizon

    def test_run_projection_recurring_expense_24_months(self):
        # Arrange — recurring expense → 24-month horizon
        svc, mock_analysis_repo, mock_goals_repo, _, mock_client = self._make_service()
        mock_analysis_repo.get_rolling_3month_averages.return_value = {
            "avg_income": 5000.0,
            "avg_expenses": 3000.0,
        }
        mock_goals_repo.get_all_goals.return_value = []
        mock_client.chat.completions.create.side_effect = Exception("no key")
        simulation_row = {
            "expense_amount": 200.0,
            "expense_type": "recurring",
            "expense_start_date": "2024-01-01",
            "expense_name": "Streaming",
        }

        # Act
        result = svc.run_projection(simulation_row)

        # Assert
        assert len(result.projection) == 24  # recurring → 24-month horizon

    def test_run_projection_with_date_object(self):
        # Arrange — start_date is already a date object (not a string)
        import datetime
        svc, mock_analysis_repo, mock_goals_repo, _, mock_client = self._make_service()
        mock_analysis_repo.get_rolling_3month_averages.return_value = {
            "avg_income": 5000.0, "avg_expenses": 3000.0,
        }
        mock_goals_repo.get_all_goals.return_value = []
        mock_client.chat.completions.create.side_effect = Exception("no key")
        simulation_row = {
            "expense_amount": 100.0,
            "expense_type": "one_time",
            "expense_start_date": datetime.date(2024, 6, 1),
            "expense_name": "Coś",
        }

        # Act — should not raise
        result = svc.run_projection(simulation_row)

        # Assert
        assert len(result.projection) == 12

    def test_run_projection_with_goal_impact(self):
        # Arrange — goal exists with allocation, triggers goal_impacts loop
        svc, mock_analysis_repo, mock_goals_repo, _, mock_client = self._make_service()
        mock_analysis_repo.get_rolling_3month_averages.return_value = {
            "avg_income": 5000.0, "avg_expenses": 3000.0,
        }
        mock_goals_repo.get_all_goals.return_value = [
            {
                "id": 1,
                "name": "Wakacje",
                "target_amount": "5000.00",
                "accumulated_progress": "1000.00",
                "monthly_allocation_amount": "500.00",
            }
        ]
        mock_client.chat.completions.create.side_effect = Exception("no key")
        simulation_row = {
            "expense_amount": 500.0,
            "expense_type": "one_time",
            "expense_start_date": "2024-06-01",
            "expense_name": "Laptop",
        }

        # Act
        result = svc.run_projection(simulation_row)

        # Assert — goal_impacts populated
        assert len(result.goal_impacts) == 1
        assert result.goal_impacts[0].goal_name == "Wakacje"

    def test_run_projection_invalid_date_string_falls_back_to_today(self):
        # Arrange — unparseable start_date triggers fallback to today
        svc, mock_analysis_repo, mock_goals_repo, _, mock_client = self._make_service()
        mock_analysis_repo.get_rolling_3month_averages.return_value = {
            "avg_income": 5000.0, "avg_expenses": 3000.0,
        }
        mock_goals_repo.get_all_goals.return_value = []
        mock_client.chat.completions.create.side_effect = Exception("no key")
        simulation_row = {
            "expense_amount": 100.0,
            "expense_type": "one_time",
            "expense_start_date": "not-a-date",
            "expense_name": "Test",
        }

        # Act — should not raise despite bad date
        result = svc.run_projection(simulation_row)

        # Assert
        assert len(result.projection) == 12

    def test_run_projection_recurring_applies_expense_from_start(self):
        # Arrange — recurring: simulated_expenses increases once start_date passed
        import datetime
        svc, mock_analysis_repo, mock_goals_repo, _, mock_client = self._make_service()
        mock_analysis_repo.get_rolling_3month_averages.return_value = {
            "avg_income": 5000.0, "avg_expenses": 3000.0,
        }
        mock_goals_repo.get_all_goals.return_value = []
        mock_client.chat.completions.create.side_effect = Exception("no key")
        past_date = (datetime.date.today() - datetime.timedelta(days=60)).isoformat()
        simulation_row = {
            "expense_amount": 200.0,
            "expense_type": "recurring",
            "expense_start_date": past_date,
            "expense_name": "Gym",
        }

        # Act
        result = svc.run_projection(simulation_row)

        # Assert — first point should have reduced simulated_surplus (past start date)
        assert result.projection[0].simulated_surplus_pln < result.projection[0].baseline_surplus_pln

    def test_build_context_summary_returns_dict(self):
        # Arrange
        svc, mock_analysis_repo, mock_goals_repo, _, _ = self._make_service()
        mock_analysis_repo.get_monthly_history.return_value = []
        mock_analysis_repo.get_financial_focus.return_value = {"label": "Oszczędności"}
        mock_goals_repo.get_all_goals.return_value = [
            {"name": "Dom", "target_amount": "200000.00",
             "accumulated_progress": "10000.00", "monthly_allocation_amount": "2000.00"},
        ]

        # Act
        result = svc._build_context_summary()

        # Assert
        assert "active_goals" in result
        assert result["financial_focus"] == "Oszczędności"
        assert len(result["active_goals"]) == 1

    def test_get_ai_recommendations_from_db_returns_empty_when_no_row(self):
        # Arrange
        svc, mock_analysis_repo, _, mock_simulations_repo, _ = self._make_service()
        mock_simulations_repo.get_current_recommendations.return_value = None
        mock_analysis_repo.count_distinct_months.return_value = 5

        # Act
        result = svc.get_ai_recommendations_from_db()

        # Assert
        assert result.insights == []
        assert result.has_sufficient_data is True

    def test_get_ai_recommendations_from_db_parses_insights(self):
        # Arrange
        svc, mock_analysis_repo, _, mock_simulations_repo, _ = self._make_service()
        mock_analysis_repo.count_distinct_months.return_value = 4
        mock_simulations_repo.get_current_recommendations.return_value = {
            "recommendations_json": [
                {"title": "Ogranicz jedzenie na mieście", "body": "Duże wydatki w restauracjach", "amount_pln": 300.0, "insight_type": "saving"},
                {"bad": "data"},  # malformed — should be skipped silently
            ],
            "generated_at": "2024-03-01T12:00:00",
            "data_through_date": "2024-02-28",
            "months_of_data": 4,
        }

        # Act
        result = svc.get_ai_recommendations_from_db()

        # Assert — 1 valid + 1 silently skipped
        assert len(result.insights) == 1
        assert result.insights[0].title == "Ogranicz jedzenie na mieście"


@pytest.mark.unit
class TestCategoriesServiceExtended:
    def _make_service(self):
        mock_db = MagicMock()
        mock_client = MagicMock()
        svc = CategoriesService(db_context=mock_db, client=mock_client)
        return svc, mock_client

    def test_build_calls_repo_and_sets_categories(self):
        # Arrange
        svc, _ = self._make_service()
        svc.categories_repository = MagicMock()
        svc.categories_repository.get_categories.return_value = [
            (1, "Jedzenie", "Wydatki"),
            (2, "Transport", "Wydatki"),
        ]

        # Act
        svc.build()

        # Assert
        assert svc.categories != ""
        assert "Jedzenie" in svc.categories
        svc.categories_repository.get_categories.assert_called_once()

    def test_assign_candidates_raises_when_no_tool_call(self):
        # Arrange
        svc, mock_client = self._make_service()
        response = MagicMock()
        response.output = []  # no function_call items
        mock_client.responses.create.return_value = response
        svc.categories = "cat_id | cat_name"
        tx = TransactionModel(
            vendor="Biedronka", title="PARAGON", products=[], total=10.0, date="2024-01-01"
        )

        # Act / Assert
        with pytest.raises(ValueError):
            svc.assign_category_candidates(tx)


@pytest.mark.unit
class TestBankCategorizationServiceExtended:
    def _make_service(self):
        mock_db = MagicMock()
        mock_db.conn = None
        mock_client = MagicMock()
        mock_async_client = MagicMock()
        svc = BankCategorizationService(
            db_context=mock_db, client=mock_client, async_client=mock_async_client
        )
        return svc, mock_client, mock_async_client

    def test_normalize_counterparty_strips_suffixes(self):
        # Arrange / Act — use ASCII city name (regex matches ASCII city patterns)
        result = _normalize_counterparty("ALDI SP. Z O.O.  PLOCK")

        # Assert — legal suffix and city stripped
        assert "SP. Z O.O." not in result
        assert result == "ALDI"

    def test_build_loads_categories_table(self):
        # Arrange
        svc, _, _ = self._make_service()
        svc.categories_repository = MagicMock()
        svc.categories_repository.get_categories.return_value = [
            (1, "Jedzenie", "Wydatki"),
        ]

        # Act
        svc.build()

        # Assert
        assert svc.categories_table != ""
        assert "Jedzenie" in svc.categories_table

    def test_assign_candidates_raises_when_no_tool_call(self):
        # Arrange
        svc, mock_client, _ = self._make_service()
        response = MagicMock()
        response.output = []  # no function_call items
        mock_client.responses.create.return_value = response
        svc.categories_table = "cat_id | cat_name"
        tx = BankTransactionDetail(
            id=1, reference_number="REF1", booking_date="2024-01-01",
            amount=50.0, currency="PLN",
        )

        # Act / Assert
        with pytest.raises(ValueError):
            svc.assign_candidates(tx)

    async def test_assign_candidates_async_raises_when_no_tool_call(self):
        # Arrange
        svc, _, mock_async_client = self._make_service()
        response = MagicMock()
        response.output = []
        mock_async_client.responses.create = AsyncMock(return_value=response)
        svc.categories_table = "cat_id | cat_name"
        import asyncio
        lock = asyncio.Lock()
        tx = BankTransactionDetail(
            id=1, reference_number="REF1", booking_date="2024-01-01",
            amount=50.0, currency="PLN",
        )

        # Act / Assert
        with pytest.raises(ValueError):
            await svc.assign_candidates_async(tx, lock)
