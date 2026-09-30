import pytest

from src.data import ProductItem, TransactionModel
from src.services.receipt_auto_confirm import (
    AutoConfirmSettings,
    ProductResolution,
    evaluate,
    normalize_score,
)

SETTINGS = AutoConfirmSettings(enabled=True, min_ai_confidence=0.9, history_min_count=2, history_min_share=0.9)


def _tx(products, total):
    return TransactionModel(vendor="Lidl", title="PARAGON FISKALNY", products=products, total=total, date="2026-09-30")


def _history(name, category_id=1):
    return ProductResolution(name, 10, "Mleko", category_id, "Nabiał", "history", 0.95, 5)


def _ai(name, confidence, category_id=2):
    return ProductResolution(name, None, None, category_id, "Pieczywo", "ai", confidence, 0)


@pytest.mark.unit
def test_all_history_and_sum_matches_is_ok():
    # Arrange
    tx = _tx([ProductItem(name="MLEKO", quantity=1, price=3.99)], 3.99)

    # Act
    decision = evaluate(tx, [_history("MLEKO")], vendor_has_history=True, settings=SETTINGS)

    # Assert
    assert decision.ok is True
    assert decision.reasons == []


@pytest.mark.unit
def test_sum_mismatch_blocks_with_polish_message():
    # Arrange
    tx = _tx([ProductItem(name="MLEKO", quantity=1, price=47.30)], 49.99)

    # Act
    decision = evaluate(tx, [_history("MLEKO")], vendor_has_history=True, settings=SETTINGS)

    # Assert
    assert decision.ok is False
    assert decision.reasons[0].code == "sum_mismatch"
    assert decision.reasons[0].message == "Suma produktów 47,30 zł ≠ 49,99 zł"
    assert decision.reasons[0].blocking is True


@pytest.mark.unit
def test_discount_lines_count_towards_sum():
    # Arrange
    tx = _tx(
        [ProductItem(name="MALINY", quantity=1, price=10.00), ProductItem(name="OPUST MALINY", quantity=1, price=-2.50)],
        7.50,
    )

    # Act
    decision = evaluate(tx, [_history("MALINY"), _history("OPUST MALINY", 3)], True, SETTINGS)

    # Assert
    assert decision.ok is True


@pytest.mark.unit
def test_sum_within_one_grosz_tolerance_is_ok():
    # Arrange
    tx = _tx([ProductItem(name="MLEKO", quantity=1, price=3.99)], 4.00)

    # Act
    decision = evaluate(tx, [_history("MLEKO")], True, SETTINGS)

    # Assert
    assert decision.ok is True


@pytest.mark.unit
def test_low_ai_confidence_blocks():
    # Arrange
    tx = _tx([ProductItem(name="SER KOZI 150G", quantity=1, price=9.99)], 9.99)

    # Act
    decision = evaluate(tx, [_ai("SER KOZI 150G", 0.62)], True, SETTINGS)

    # Assert
    assert decision.ok is False
    assert decision.reasons[0].code == "low_confidence"
    assert decision.reasons[0].message == 'Nowy produkt „SER KOZI 150G”: pewność AI 62%'


@pytest.mark.unit
def test_high_ai_confidence_passes():
    # Arrange
    tx = _tx([ProductItem(name="BULKA", quantity=1, price=0.99)], 0.99)

    # Act
    decision = evaluate(tx, [_ai("BULKA", 0.93)], True, SETTINGS)

    # Assert
    assert decision.ok is True


@pytest.mark.unit
def test_product_without_resolution_blocks():
    # Arrange
    tx = _tx([ProductItem(name="X", quantity=1, price=1.0)], 1.0)

    # Act
    decision = evaluate(tx, [], True, SETTINGS)

    # Assert
    assert decision.ok is False
    assert decision.reasons[0].code == "no_category"
    assert decision.reasons[0].message == 'Brak kategorii dla „X”'


@pytest.mark.unit
def test_new_vendor_is_non_blocking_reason():
    # Arrange
    tx = _tx([ProductItem(name="MLEKO", quantity=1, price=3.99)], 3.99)

    # Act
    decision = evaluate(tx, [_history("MLEKO")], vendor_has_history=False, settings=SETTINGS)

    # Assert
    assert decision.ok is True
    assert [(r.code, r.blocking) for r in decision.reasons] == [("vendor_new", False)]
    assert decision.reasons[0].message == 'Pierwszy paragon ze sklepu „Lidl”'


@pytest.mark.unit
@pytest.mark.parametrize("raw,expected", [(0.87, 0.87), (87.0, 0.87), (1.0, 1.0), (0.0, 0.0)])
def test_normalize_score_accepts_fraction_or_percent(raw, expected):
    # Act / Assert
    assert normalize_score(raw) == pytest.approx(expected)


@pytest.mark.unit
def test_settings_from_env(monkeypatch):
    # Arrange
    monkeypatch.setenv("RECEIPT_AUTO_CONFIRM_ENABLED", "true")
    monkeypatch.setenv("RECEIPT_AUTO_CONFIRM_MIN_AI_CONFIDENCE", "0.8")
    monkeypatch.setenv("RECEIPT_AUTO_CONFIRM_HISTORY_MIN_COUNT", "3")
    monkeypatch.setenv("RECEIPT_AUTO_CONFIRM_HISTORY_MIN_SHARE", "0.75")

    # Act
    settings = AutoConfirmSettings.from_env()

    # Assert
    assert settings == AutoConfirmSettings(True, 0.8, 3, 0.75)


@pytest.mark.unit
def test_settings_from_env_defaults_disabled(monkeypatch):
    # Arrange
    for key in (
        "RECEIPT_AUTO_CONFIRM_ENABLED",
        "RECEIPT_AUTO_CONFIRM_MIN_AI_CONFIDENCE",
        "RECEIPT_AUTO_CONFIRM_HISTORY_MIN_COUNT",
        "RECEIPT_AUTO_CONFIRM_HISTORY_MIN_SHARE",
    ):
        monkeypatch.delenv(key, raising=False)

    # Act
    settings = AutoConfirmSettings.from_env()

    # Assert
    assert settings == AutoConfirmSettings()
