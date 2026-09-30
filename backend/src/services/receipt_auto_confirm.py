from __future__ import annotations

import os
from dataclasses import dataclass

from ..data import TransactionModel

SOURCE_HISTORY = "history"
SOURCE_AI = "ai"
SUM_TOLERANCE = 0.01


@dataclass(frozen=True)
class AutoConfirmSettings:
    enabled: bool = False
    min_ai_confidence: float = 0.9
    history_min_count: int = 2
    history_min_share: float = 0.9

    @classmethod
    def from_env(cls) -> "AutoConfirmSettings":
        enabled_raw = os.getenv("RECEIPT_AUTO_CONFIRM_ENABLED", "false").strip().lower()
        return cls(
            enabled=enabled_raw in ("1", "true", "yes"),
            min_ai_confidence=float(os.getenv("RECEIPT_AUTO_CONFIRM_MIN_AI_CONFIDENCE", "0.9")),
            history_min_count=int(os.getenv("RECEIPT_AUTO_CONFIRM_HISTORY_MIN_COUNT", "2")),
            history_min_share=float(os.getenv("RECEIPT_AUTO_CONFIRM_HISTORY_MIN_SHARE", "0.9")),
        )


@dataclass(frozen=True)
class ProductResolution:
    raw_name: str
    product_id: int | None
    normalized_name: str | None
    category_id: int | None
    category_name: str | None
    source: str | None
    confidence: float
    history_count: int = 0


@dataclass(frozen=True)
class AutoConfirmReason:
    code: str
    message: str
    blocking: bool

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "blocking": self.blocking}


@dataclass(frozen=True)
class AutoConfirmDecision:
    ok: bool
    reasons: list[AutoConfirmReason]


def normalize_score(score: float) -> float:
    return score / 100.0 if score > 1.0 else score


def evaluation_error_reason() -> AutoConfirmReason:
    return AutoConfirmReason("evaluation_error", "Nie udało się ocenić automatycznie", True)


def confirm_failed_reason() -> AutoConfirmReason:
    return AutoConfirmReason("confirm_failed", "Automatyczne potwierdzenie nie powiodło się", True)


def _pln(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + " zł"


def evaluate(
    transaction: TransactionModel,
    resolutions: list[ProductResolution],
    vendor_has_history: bool,
    settings: AutoConfirmSettings,
) -> AutoConfirmDecision:
    reasons: list[AutoConfirmReason] = []

    products_sum = round(sum(p.price for p in transaction.products), 2)
    if abs(products_sum - transaction.total) > SUM_TOLERANCE + 1e-9:
        reasons.append(
            AutoConfirmReason(
                "sum_mismatch",
                f"Suma produktów {_pln(products_sum)} ≠ {_pln(transaction.total)}",
                True,
            )
        )

    by_name = {r.raw_name: r for r in resolutions}
    for name in dict.fromkeys(p.name for p in transaction.products):
        resolution = by_name.get(name)
        if resolution is None or resolution.category_id is None:
            reasons.append(AutoConfirmReason("no_category", f"Brak kategorii dla „{name}”", True))
        elif resolution.source == SOURCE_AI and resolution.confidence < settings.min_ai_confidence:
            reasons.append(
                AutoConfirmReason(
                    "low_confidence",
                    f"Nowy produkt „{name}”: pewność AI {round(resolution.confidence * 100)}%",
                    True,
                )
            )

    if not vendor_has_history:
        reasons.append(
            AutoConfirmReason("vendor_new", f"Pierwszy paragon ze sklepu „{transaction.vendor}”", False)
        )

    return AutoConfirmDecision(ok=not any(r.blocking for r in reasons), reasons=reasons)
