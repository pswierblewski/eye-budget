from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime

from pydantic import ValidationError

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class OcrValidationResult:
    ok: bool
    errors: list[str]
    normalized: dict | None = None


def validate_ocr_payload(data: dict) -> OcrValidationResult:
    errors: list[str] = []

    vendor = data.get("vendor")
    if not isinstance(vendor, str) or not vendor.strip():
        errors.append("Brak nazwy sklepu (vendor).")

    date_raw = data.get("date")
    date_str = date_raw.strip() if isinstance(date_raw, str) else ""
    if not date_str:
        errors.append("Brak daty transakcji.")
    elif not _ISO_DATE.match(date_str):
        errors.append("Niepoprawny format daty (oczekiwano RRRR-MM-DD).")
    else:
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            errors.append("Niepoprawny format daty (oczekiwano RRRR-MM-DD).")

    total_raw = data.get("total")
    try:
        total_f = float(total_raw)
    except (TypeError, ValueError):
        errors.append("Brak kwoty całkowitej (total).")
        total_f = None
    if total_f is not None and total_f == 0:
        errors.append("Kwota całkowita nie może być zero.")

    products = data.get("products")
    if not isinstance(products, list) or len(products) < 1:
        errors.append("Brak pozycji na paragonie.")
    else:
        for i, product in enumerate(products, start=1):
            if not isinstance(product, dict):
                errors.append(f"Pozycja {i}: nieprawidłowy format.")
                continue
            name = product.get("name")
            if not isinstance(name, str) or not name.strip():
                errors.append(f"Pozycja {i}: brak nazwy produktu.")

    if errors:
        return OcrValidationResult(ok=False, errors=errors, normalized=None)

    normalized = copy.deepcopy(data)
    if isinstance(vendor, str):
        normalized["vendor"] = vendor.strip()
    normalized["date"] = date_str
    return OcrValidationResult(ok=True, errors=[], normalized=normalized)


def format_pydantic_validation_error(exc: ValidationError) -> str:
    parts: list[str] = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", ()))
        parts.append(loc or "pole")
    detail = ", ".join(parts[:5])
    return f"Niepełne dane paragonu: {detail}."
