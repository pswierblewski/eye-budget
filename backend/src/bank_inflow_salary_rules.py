"""Deterministic inflow salary detection from bank counterparty (before LLM)."""
from __future__ import annotations

import re
import unicodedata
from typing import Literal

SalaryRule = Literal["pensja_pawel", "pensja_ada"]

# Normalized reference (ASCII) for "Software Engineering Paweł Świerblewski"
_REF_PAWEL_ASCII = "software engineering pawel swierblewski"
_SUB_PERN = "pern"


def _collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def _to_ascii_lower(s: str) -> str:
    nkfd = unicodedata.normalize("NFKD", s)
    stripped = "".join(c for c in nkfd if unicodedata.category(c) != "Mn")
    return stripped.casefold()


def try_deterministic_inflow_salary_rule(counterparty: str | None) -> SalaryRule | None:
    """
    If counterparty matches employer rules, return which Pensja bucket applies.
    Order: longer / more specific (Paweł full name) before Pern substring.
    Matching is case-insensitive; diacritics tolerated via Unicode casefold path.
    """
    if not counterparty:
        return None
    collapsed = _collapse_spaces(counterparty)
    haystack_cf = collapsed.casefold()
    haystack_ascii = _to_ascii_lower(collapsed)

    if _REF_PAWEL_ASCII in haystack_ascii:
        return "pensja_pawel"
    ref_pawel_cf = "software engineering paweł świerblewski".casefold()
    if ref_pawel_cf in haystack_cf:
        return "pensja_pawel"

    if _SUB_PERN in haystack_ascii or _SUB_PERN in haystack_cf:
        return "pensja_ada"

    return None
