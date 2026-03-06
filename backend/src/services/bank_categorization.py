"""
Service for assigning category candidates to bank transactions using LLM.

Mirrors the logic of CategoriesService (for receipt products) but adapted
for single-category assignment per bank transaction (no per-product breakdown).

Context priority:
  1. Receipts with matching vendor — top categories from receipt_transaction_items
     (most accurate: reflects what the user actually buys at that store).
  2. Confirmed bank transactions with a similar counterparty
     (fallback when no receipts are available yet).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from abc import ABC

from openai import AsyncOpenAI, OpenAI

from ..repositories.categories import CategoriesRepository
from ..services.markdown_table import MarkdownTableService
from ..data import BankTransactionDetail, CategoryCandidatesTransaction


# Patterns to strip from the end of counterparty strings when building the
# vendor lookup key (city names, legal forms, etc.)
_STRIP_SUFFIXES = re.compile(
    r"\s+(SP\.?\s*Z\s*O\.?\s*O\.?|S\.?A\.?|SP\.?\s*J\.?|SP\.?\s*K\.?|"
    r"PLOCK|POZNAN|WARSZAWA|KRAKOW|GDANSK|WROCLAW|LODZ|KATOWICE|BIALYSTOK|"
    r"TORUN|LUBLIN|SZCZECIN|GDYNIA|BYDGOSZCZ|RZESZOW|OLSZTYN|ZIELONA\s*GORA|"
    r"OPOLE|GORZOW\s*WLKP)$",
    re.IGNORECASE,
)


def _normalize_counterparty(counterparty: str) -> str:
    """Strip city/legal suffixes so 'ALDI SP. Z O.O.  PLOCK' becomes 'ALDI'."""
    result = counterparty.strip().upper()
    for _ in range(5):  # run multiple passes to strip layered suffixes
        new = _STRIP_SUFFIXES.sub("", result).strip()
        if new == result:
            break
        result = new
    return result


class BankCategorizationService(ABC):
    SYSTEM_PROMPT = (
        "Jesteś ekspertem od polskich transakcji bankowych i budżetowania domowego. "
        "Przypisz jedną lub kilka najbardziej trafnych kategorii budżetowych do podanej "
        "transakcji bankowej. Podaj kandydatów posortowanych od najbardziej do najmniej "
        "pasującego, z wynikiem pewności (0.0–1.0)."
    )

    USER_PROMPT_TEMPLATE = """
Poniżej znajduje się lista dostępnych kategorii:
================
{categories_table}
================

Dane transakcji bankowej:
================
Kontrahent:   {counterparty}
Opis:         {description}
Typ operacji: {operation_type}
Kwota:        {amount} {currency}
Data:         {booking_date}
================
{context_section}
Zwróć kandydatów na kategorię z wynikiem pewności dla tej transakcji.
"""

    def __init__(self, db_context):
        self.categories_repository = CategoriesRepository(db_context=db_context)
        self.markdown_table_service = MarkdownTableService()
        self.client = OpenAI()
        self.async_client = AsyncOpenAI()
        self.model = os.getenv("MODEL", "gpt-5.2")
        self.categories_table = ""
        self._conn = db_context.conn

    def build(self) -> None:
        """Pre-load the categories markdown table (call once at App init)."""
        categories = self.categories_repository.get_categories()
        ids = ["category_id"]
        names = ["category_name"]
        parents = ["category_parent_name"]
        for cat in categories:
            ids.append(cat[0])
            names.append(cat[1])
            parents.append(cat[2])
        self.categories_table = self.markdown_table_service.table(
            [ids, names, parents]
        )

    def assign_candidates(self, tx: BankTransactionDetail) -> list[dict]:
        """
        Call the LLM to assign category candidates to a bank transaction.

        Returns a list of dicts: [{category_id, category_name, category_score}, ...]
        """
        tool_name = "assign_bank_transaction_category"
        tools = [
            {
                "type": "function",
                "name": tool_name,
                "description": "Assign category candidates to a bank transaction",
                "parameters": CategoryCandidatesTransaction.model_json_schema(),
            }
        ]

        context_section = self._build_context_section(tx.counterparty or "")

        prompt = self.USER_PROMPT_TEMPLATE.format(
            categories_table=self.categories_table,
            counterparty=tx.counterparty or "(brak)",
            description=tx.description or "(brak)",
            operation_type=tx.operation_type or "(brak)",
            amount=tx.amount,
            currency=tx.currency,
            booking_date=tx.booking_date,
            context_section=context_section,
        )

        response = self.client.responses.create(
            model=self.model,
            reasoning={"effort": "medium"},
            tools=tools,
            tool_choice={"type": "function", "name": tool_name},
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
        )

        tool_call = next(
            (item for item in response.output if item.type == "function_call"),
            None,
        )
        if tool_call is None:
            raise ValueError("No function call in LLM response for bank transaction categorization")

        args = json.loads(tool_call.arguments)
        return args.get("category_candidates", [])

    async def assign_candidates_async(
        self,
        tx: BankTransactionDetail,
        db_lock: asyncio.Lock,
    ) -> list[dict]:
        """Async version of assign_candidates — builds context with db_lock, awaits LLM call."""
        tool_name = "assign_bank_transaction_category"
        tools = [
            {
                "type": "function",
                "name": tool_name,
                "description": "Assign category candidates to a bank transaction",
                "parameters": CategoryCandidatesTransaction.model_json_schema(),
            }
        ]

        # DB-bound context queries serialised through the lock
        async with db_lock:
            context_section = await asyncio.to_thread(
                self._build_context_section, tx.counterparty or ""
            )

        prompt = self.USER_PROMPT_TEMPLATE.format(
            categories_table=self.categories_table,
            counterparty=tx.counterparty or "(brak)",
            description=tx.description or "(brak)",
            operation_type=tx.operation_type or "(brak)",
            amount=tx.amount,
            currency=tx.currency,
            booking_date=tx.booking_date,
            context_section=context_section,
        )

        response = await self.async_client.responses.create(
            model=self.model,
            reasoning={"effort": "medium"},
            tools=tools,
            tool_choice={"type": "function", "name": tool_name},
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": prompt}],
                }
            ],
        )

        tool_call = next(
            (item for item in response.output if item.type == "function_call"),
            None,
        )
        if tool_call is None:
            raise ValueError("No function call in LLM response for bank transaction categorization")

        args = json.loads(tool_call.arguments)
        return args.get("category_candidates", [])

    # ------------------------------------------------------------------
    # Context building
    # ------------------------------------------------------------------

    def _build_context_section(self, counterparty: str) -> str:
        if not counterparty or not self._conn:
            return ""

        norm = _normalize_counterparty(counterparty)
        receipt_context = self._get_receipt_context(norm)
        bank_context = self._get_bank_context(norm)

        parts: list[str] = []
        if receipt_context:
            parts.append("Poprzednie zakupy u tego sprzedawcy (z paragonów — PRIORYTET):\n" + receipt_context)
        if bank_context:
            parts.append("Poprzednie transakcje bankowe u tego kontrahenta:\n" + bank_context)

        if not parts:
            return ""
        return "Kontekst historyczny:\n================\n" + "\n\n".join(parts) + "\n================\n"

    def _get_receipt_context(self, norm: str) -> str:
        """
        Find top-5 categories used for products bought at this vendor (from confirmed receipts).

        Strategy:
          1. Exact match: vendors_alternative_names.name ILIKE norm
          2. Fuzzy match: vendors.name ILIKE norm  (normalized vendor name)
        Both give us vendor_id → receipt_transaction_items → category counts.
        """
        if not self._conn:
            return ""
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    WITH matched_vendor AS (
                        SELECT DISTINCT v.id AS vendor_id
                        FROM vendors v
                        LEFT JOIN vendors_alternative_names van ON van.vendor = v.id
                        WHERE van.name ILIKE %s
                           OR v.name ILIKE %s
                        LIMIT 1
                    )
                    SELECT c.name AS category_name, COUNT(*) AS cnt
                    FROM matched_vendor mv
                    JOIN receipt_transactions rt ON rt.vendor_id = mv.vendor_id
                    JOIN receipt_transaction_items rti ON rti.transaction_id = rt.id
                    JOIN categories c ON c.id = rti.category_id
                    GROUP BY c.name
                    ORDER BY cnt DESC
                    LIMIT 5
                    """,
                    (f"%{norm}%", f"%{norm}%"),
                )
                rows = cur.fetchall()
        except Exception as e:
            print(f"BankCategorizationService._get_receipt_context error: {e}")
            return ""

        if not rows:
            return ""
        lines = [f"  - {r[0]} ({r[1]}x)" for r in rows]
        return "\n".join(lines)

    def _get_bank_context(self, norm: str) -> str:
        """
        Up to 5 most recent confirmed bank transactions with a similar counterparty.
        """
        if not self._conn:
            return ""
        try:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bt.counterparty, bt.description, bt.amount, c.name
                    FROM bank_transactions bt
                    JOIN categories c ON c.id = bt.category_id
                    WHERE bt.counterparty ILIKE %s
                    ORDER BY bt.booking_date DESC
                    LIMIT 5
                    """,
                    (f"%{norm}%",),
                )
                rows = cur.fetchall()
        except Exception as e:
            print(f"BankCategorizationService._get_bank_context error: {e}")
            return ""

        if not rows:
            return ""
        lines = [
            f"  - Kontrahent: {r[0]}, Opis: {r[1]}, Kwota: {r[2]}, Kategoria: {r[3]}"
            for r in rows
        ]
        return "\n".join(lines)
