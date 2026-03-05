"""
Repository that produces a unified, deduplicated transaction list from
bank_transactions, cash_transactions, and unlinked receipts.

Deduplication rule:
  - bank_transactions  → always included (has_receipt=True when linked to a receipt)
  - cash_transactions  → always included (has_receipt=True when linked to a receipt)
  - receipts           → only included when NOT linked to any bank or cash transaction
"""
from __future__ import annotations

import datetime
from typing import Optional

from ..data import (
    UnifiedTransaction,
    ReceiptCategory,
    MonthlySummary,
    CategoryBreakdown,
    VendorBreakdown,
    MonthOverMonth,
    AnalyticsSummary,
)


# Columns we allow sorting on in the outer wrapper query.
_SORT_COLS: dict[str, str] = {
    "date":           "date",
    "amount":         "amount",
    "description":    "description",
    "category_name":  "category_name",
    "status":         "status",
    "source_type":    "source_type",
}


class UnifiedTransactionsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    # ------------------------------------------------------------------
    # List
    # ------------------------------------------------------------------

    def get_list(
        self,
        status: Optional[str] = None,
        source_type: Optional[str] = None,   # 'bank' | 'cash' | 'receipt'
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        category_id: Optional[int] = None,
        tag: Optional[str] = None,
        search: Optional[str] = None,
        amount_min: Optional[float] = None,
        amount_max: Optional[float] = None,
        sort_by: str = "date",
        sort_dir: str = "desc",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[UnifiedTransaction], int]:
        """Return unified transactions, paginated and filtered."""
        if not self.conn:
            return [], 0

        order_expr = _SORT_COLS.get(sort_by, "date")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
        order_clause = f"{order_expr} {direction} NULLS LAST" + (
            ", id DESC" if order_expr != "id" else ""
        )

        # ------------------------------------------------------------------
        # Build outer WHERE conditions applied after UNION ALL
        # ------------------------------------------------------------------
        conditions: list[str] = []
        params: list = []

        if status:
            conditions.append("status = %s")
            params.append(status)
        if source_type:
            conditions.append("source_type = %s")
            params.append(source_type)
        if date_from:
            conditions.append("date >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("date <= %s")
            params.append(date_to)
        if category_id is not None:
            conditions.append("category_id = %s")
            params.append(category_id)
        if tag:
            conditions.append("%s = ANY(tags)")
            params.append(tag)
        if search:
            conditions.append("(description ILIKE %s OR vendor_name ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        if amount_min is not None:
            conditions.append("amount >= %s")
            params.append(amount_min)
        if amount_max is not None:
            conditions.append("amount <= %s")
            params.append(amount_max)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        id, source_type, date, amount, description,
                        vendor_name, category_id, category_name, category_group_name,
                        tags, status, has_receipt, receipt_scan_id, currency,
                        receipt_category_name, receipt_category_count,
                        receipt_categories,
                        COUNT(*) OVER () AS total_count
                    FROM (
                        -- ── Bank transactions ──────────────────────────────────────
                        SELECT
                            bt.id,
                            'bank'::text AS source_type,
                            bt.booking_date::date AS date,
                            bt.amount::float,
                            COALESCE(bt.counterparty, bt.description) AS description,
                            v.name AS vendor_name,
                            bt.category_id,
                            c.name AS category_name,
                            cg.name AS category_group_name,
                            bt.tags,
                            bt.status,
                            (rbl.bank_transaction_id IS NOT NULL) AS has_receipt,
                            rbl_scan.scan_id AS receipt_scan_id,
                            bt.currency,
                            (
                                SELECT CONCAT_WS(' / ', cg2.name, pc.name, cat.name)
                                FROM receipt_bank_links rbl2
                                JOIN receipt_transaction_items rti ON rti.transaction_id = rbl2.receipt_transaction_id
                                JOIN categories cat ON cat.id = rti.category_id
                                LEFT JOIN category_groups cg2 ON cg2.id = cat.category_group_id
                                LEFT JOIN categories pc ON pc.id = cat.parent_id
                                WHERE rbl2.bank_transaction_id = bt.id
                                GROUP BY cat.id, cat.name, cg2.name, pc.name
                                ORDER BY COUNT(*) DESC
                                LIMIT 1
                            ) AS receipt_category_name,
                            (
                                SELECT COUNT(DISTINCT rti.category_id)
                                FROM receipt_bank_links rbl2
                                JOIN receipt_transaction_items rti ON rti.transaction_id = rbl2.receipt_transaction_id
                                WHERE rbl2.bank_transaction_id = bt.id
                            ) AS receipt_category_count,
                            (
                                SELECT json_agg(
                                    json_build_object('id', cat_id, 'name', cat_name, 'product_count', cnt)
                                    ORDER BY cnt DESC
                                )
                                FROM (
                                    SELECT rti.category_id AS cat_id, CONCAT_WS(' / ', cg2.name, pc.name, cat.name) AS cat_name, COUNT(*) AS cnt
                                    FROM receipt_bank_links rbl2
                                    JOIN receipt_transaction_items rti ON rti.transaction_id = rbl2.receipt_transaction_id
                                    JOIN categories cat ON cat.id = rti.category_id
                                    LEFT JOIN category_groups cg2 ON cg2.id = cat.category_group_id
                                    LEFT JOIN categories pc ON pc.id = cat.parent_id
                                    WHERE rbl2.bank_transaction_id = bt.id
                                    GROUP BY rti.category_id, cat.id, cat.name, cg2.name, pc.name
                                ) AS cats
                            ) AS receipt_categories
                        FROM bank_transactions bt
                        LEFT JOIN categories c ON c.id = bt.category_id
                        LEFT JOIN category_groups cg ON cg.id = c.category_group_id
                        LEFT JOIN vendors v ON v.id = bt.vendor_id
                        LEFT JOIN receipt_bank_links rbl ON rbl.bank_transaction_id = bt.id
                        LEFT JOIN receipt_transactions rbl_scan ON rbl_scan.id = rbl.receipt_transaction_id

                        UNION ALL

                        -- ── Cash transactions ──────────────────────────────────────
                        SELECT
                            ct.id,
                            'cash'::text AS source_type,
                            ct.booking_date::date AS date,
                            ct.amount::float,
                            ct.description,
                            v.name AS vendor_name,
                            ct.category_id,
                            c.name AS category_name,
                            cg.name AS category_group_name,
                            ct.tags,
                            ct.status,
                            (rcl.cash_transaction_id IS NOT NULL) AS has_receipt,
                            rcl_scan.scan_id AS receipt_scan_id,
                            ct.currency,
                            (
                                SELECT CONCAT_WS(' / ', cg2.name, pc.name, cat.name)
                                FROM receipt_cash_links rcl2
                                JOIN receipt_transaction_items rti ON rti.transaction_id = rcl2.receipt_transaction_id
                                JOIN categories cat ON cat.id = rti.category_id
                                LEFT JOIN category_groups cg2 ON cg2.id = cat.category_group_id
                                LEFT JOIN categories pc ON pc.id = cat.parent_id
                                WHERE rcl2.cash_transaction_id = ct.id
                                GROUP BY cat.id, cat.name, cg2.name, pc.name
                                ORDER BY COUNT(*) DESC
                                LIMIT 1
                            ) AS receipt_category_name,
                            (
                                SELECT COUNT(DISTINCT rti.category_id)
                                FROM receipt_cash_links rcl2
                                JOIN receipt_transaction_items rti ON rti.transaction_id = rcl2.receipt_transaction_id
                                WHERE rcl2.cash_transaction_id = ct.id
                            ) AS receipt_category_count,
                            (
                                SELECT json_agg(
                                    json_build_object('id', cat_id, 'name', cat_name, 'product_count', cnt)
                                    ORDER BY cnt DESC
                                )
                                FROM (
                                    SELECT rti.category_id AS cat_id, CONCAT_WS(' / ', cg2.name, pc.name, cat.name) AS cat_name, COUNT(*) AS cnt
                                    FROM receipt_cash_links rcl2
                                    JOIN receipt_transaction_items rti ON rti.transaction_id = rcl2.receipt_transaction_id
                                    JOIN categories cat ON cat.id = rti.category_id
                                    LEFT JOIN category_groups cg2 ON cg2.id = cat.category_group_id
                                    LEFT JOIN categories pc ON pc.id = cat.parent_id
                                    WHERE rcl2.cash_transaction_id = ct.id
                                    GROUP BY rti.category_id, cat.id, cat.name, cg2.name, pc.name
                                ) AS cats
                            ) AS receipt_categories
                        FROM cash_transactions ct
                        LEFT JOIN categories c ON c.id = ct.category_id
                        LEFT JOIN category_groups cg ON cg.id = c.category_group_id
                        LEFT JOIN vendors v ON v.id = ct.vendor_id
                        LEFT JOIN receipt_cash_links rcl ON rcl.cash_transaction_id = ct.id
                        LEFT JOIN receipt_transactions rcl_scan ON rcl_scan.id = rcl.receipt_transaction_id

                        UNION ALL

                        -- ── Unlinked receipts ──────────────────────────────────────
                        SELECT
                            rs.id,
                            'receipt'::text AS source_type,
                            rt.date::date AS date,
                            -(rt.total)::float AS amount,
                            COALESCE(v.name, rt.raw_vendor_name, rs.filename) AS description,
                            COALESCE(v.name, rt.raw_vendor_name) AS vendor_name,
                            NULL::int AS category_id,
                            NULL::text AS category_name,
                            NULL::text AS category_group_name,
                            rs.tags,
                            rs.status::text,
                            FALSE AS has_receipt,
                            rs.id AS receipt_scan_id,
                            'PLN'::text AS currency,
                            NULL::text AS receipt_category_name,
                            NULL::int AS receipt_category_count,
                            NULL::json AS receipt_categories
                        FROM receipts_scans rs
                        JOIN receipt_transactions rt ON rt.scan_id = rs.id
                        LEFT JOIN vendors v ON v.id = rt.vendor_id
                        LEFT JOIN receipt_bank_links rbl ON rbl.receipt_transaction_id = rt.id
                        LEFT JOIN receipt_cash_links rcl ON rcl.receipt_transaction_id = rt.id
                        WHERE rbl.bank_transaction_id IS NULL
                          AND rcl.cash_transaction_id IS NULL
                          AND rs.status IN ('to_confirm', 'done')
                    ) AS unified
                    {where}
                    ORDER BY {order_clause}
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                rows = cur.fetchall()

            total = int(rows[0][17]) if rows else 0
            return [
                UnifiedTransaction(
                    id=r[0],
                    source_type=r[1],
                    date=r[2].isoformat() if isinstance(r[2], datetime.date) else str(r[2]),
                    amount=float(r[3]),
                    description=r[4],
                    vendor_name=r[5],
                    category_id=r[6],
                    category_name=r[7],
                    category_group_name=r[8],
                    tags=list(r[9]) if r[9] else [],
                    status=r[10],
                    has_receipt=bool(r[11]),
                    receipt_scan_id=r[12],
                    currency=r[13] or "PLN",
                    receipt_category_name=r[14],
                    receipt_category_count=int(r[15]) if r[15] is not None else None,
                    receipt_categories=[
                        ReceiptCategory(id=cat['id'], name=cat['name'], product_count=cat['product_count'])
                        for cat in (r[16] or [])
                    ] or None,
                )
                for r in rows
            ], total
        except Exception as e:
            print(f"UnifiedTransactionsRepository.get_list error: {e}")
            import traceback; traceback.print_exc()
            return [], 0

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def get_analytics(
        self,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> AnalyticsSummary:
        """Return aggregated analytics for the given date range."""
        if not self.conn:
            return _empty_analytics()

        # Default: last 12 full months + current month
        if not date_from:
            date_from = (datetime.date.today().replace(day=1) - datetime.timedelta(days=365)).isoformat()
        if not date_to:
            date_to = datetime.date.today().isoformat()

        try:
            with self.conn.cursor() as cur:
                # ── 1. Top-level totals ────────────────────────────────
                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0)::float,
                        COALESCE(SUM(CASE WHEN amount > 0 THEN  amount ELSE 0 END), 0)::float,
                        COUNT(*)::int
                    FROM (
                        SELECT bt.amount::float AS amount, bt.booking_date AS date
                        FROM bank_transactions bt
                        UNION ALL
                        SELECT ct.amount::float AS amount, ct.booking_date AS date
                        FROM cash_transactions ct
                        LEFT JOIN receipt_cash_links rcl ON rcl.cash_transaction_id = ct.id
                        WHERE rcl.cash_transaction_id IS NULL   -- exclude if already counted via receipt link
                        UNION ALL
                        SELECT -(rt.total)::float AS amount, rt.date AS date
                        FROM receipt_transactions rt
                        LEFT JOIN receipt_bank_links rbl ON rbl.receipt_transaction_id = rt.id
                        LEFT JOIN receipt_cash_links rcl ON rcl.receipt_transaction_id = rt.id
                        WHERE rbl.bank_transaction_id IS NULL AND rcl.cash_transaction_id IS NULL
                    ) t
                    WHERE date BETWEEN %s AND %s
                    """,
                    (date_from, date_to),
                )
                row = cur.fetchone()
                total_expense = float(row[0]) if row else 0.0
                total_income = float(row[1]) if row else 0.0
                transaction_count = int(row[2]) if row else 0

                # ── 2. Monthly totals (bank + cash only, no double-count) ──
                cur.execute(
                    """
                    SELECT
                        TO_CHAR(date, 'YYYY-MM') AS month,
                        COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0)::float AS expense,
                        COALESCE(SUM(CASE WHEN amount > 0 THEN  amount ELSE 0 END), 0)::float AS income
                    FROM (
                        SELECT bt.amount::float AS amount, bt.booking_date AS date
                        FROM bank_transactions bt
                        WHERE bt.booking_date BETWEEN %s AND %s

                        UNION ALL

                        SELECT ct.amount::float AS amount, ct.booking_date AS date
                        FROM cash_transactions ct
                        LEFT JOIN receipt_cash_links rcl ON rcl.cash_transaction_id = ct.id
                        WHERE ct.booking_date BETWEEN %s AND %s
                          AND rcl.cash_transaction_id IS NULL
                    ) t
                    GROUP BY month
                    ORDER BY month
                    """,
                    (date_from, date_to, date_from, date_to),
                )
                monthly_rows = cur.fetchall()
                monthly_totals = [
                    MonthlySummary(month=r[0], expense=float(r[1]), income=float(r[2]))
                    for r in monthly_rows
                ]

                # ── 3. By category group ─────────────────────────────────
                cur.execute(
                    """
                    SELECT
                        COALESCE(cg.name, 'Bez kategorii') AS group_name,
                        COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END), 0)::float AS total
                    FROM (
                        SELECT bt.amount::float AS amount, bt.category_id, bt.booking_date AS date
                        FROM bank_transactions bt
                        WHERE bt.booking_date BETWEEN %s AND %s AND bt.amount < 0

                        UNION ALL

                        SELECT ct.amount::float AS amount, ct.category_id, ct.booking_date AS date
                        FROM cash_transactions ct
                        LEFT JOIN receipt_cash_links rcl ON rcl.cash_transaction_id = ct.id
                        WHERE ct.booking_date BETWEEN %s AND %s
                          AND ct.amount < 0
                          AND rcl.cash_transaction_id IS NULL
                    ) t
                    LEFT JOIN categories c ON c.id = t.category_id
                    LEFT JOIN category_groups cg ON cg.id = c.category_group_id
                    GROUP BY group_name
                    ORDER BY total DESC
                    LIMIT 10
                    """,
                    (date_from, date_to, date_from, date_to),
                )
                by_category_group = [
                    CategoryBreakdown(name=r[0], total=float(r[1]))
                    for r in cur.fetchall()
                ]

                # ── 4. By vendor (top 10) ───────────────────────────────
                cur.execute(
                    """
                    SELECT
                        COALESCE(v.name, 'Nieznany') AS vendor_name,
                        SUM(-amount)::float AS total
                    FROM (
                        SELECT bt.amount::float, bt.vendor_id, bt.booking_date AS date
                        FROM bank_transactions bt
                        WHERE bt.booking_date BETWEEN %s AND %s AND bt.amount < 0

                        UNION ALL

                        SELECT ct.amount::float, ct.vendor_id, ct.booking_date AS date
                        FROM cash_transactions ct
                        LEFT JOIN receipt_cash_links rcl ON rcl.cash_transaction_id = ct.id
                        WHERE ct.booking_date BETWEEN %s AND %s
                          AND ct.amount < 0
                          AND rcl.cash_transaction_id IS NULL
                    ) t
                    LEFT JOIN vendors v ON v.id = t.vendor_id
                    WHERE v.name IS NOT NULL
                    GROUP BY vendor_name
                    ORDER BY total DESC
                    LIMIT 10
                    """,
                    (date_from, date_to, date_from, date_to),
                )
                by_vendor = [
                    VendorBreakdown(vendor_name=r[0], total=float(r[1]))
                    for r in cur.fetchall()
                ]

                # ── 5. By category (leaf, top 15) ───────────────────────
                cur.execute(
                    """
                    SELECT
                        COALESCE(c.name, 'Bez kategorii') AS category_name,
                        COALESCE(cg.name, '') AS group_name,
                        SUM(-amount)::float AS total
                    FROM (
                        SELECT bt.amount::float, bt.category_id, bt.booking_date AS date
                        FROM bank_transactions bt
                        WHERE bt.booking_date BETWEEN %s AND %s AND bt.amount < 0

                        UNION ALL

                        SELECT ct.amount::float, ct.category_id, ct.booking_date AS date
                        FROM cash_transactions ct
                        LEFT JOIN receipt_cash_links rcl ON rcl.cash_transaction_id = ct.id
                        WHERE ct.booking_date BETWEEN %s AND %s
                          AND ct.amount < 0
                          AND rcl.cash_transaction_id IS NULL
                    ) t
                    LEFT JOIN categories c ON c.id = t.category_id
                    LEFT JOIN category_groups cg ON cg.id = c.category_group_id
                    GROUP BY category_name, group_name
                    ORDER BY total DESC
                    LIMIT 15
                    """,
                    (date_from, date_to, date_from, date_to),
                )
                by_category = [
                    CategoryBreakdown(name=r[0], group_name=r[1] or None, total=float(r[2]))
                    for r in cur.fetchall()
                ]

                # ── 6. Month-over-month ──────────────────────────────────
                today = datetime.date.today()
                first_this_month = today.replace(day=1)
                last_month_end = first_this_month - datetime.timedelta(days=1)
                first_last_month = last_month_end.replace(day=1)

                cur.execute(
                    """
                    SELECT
                        COALESCE(SUM(CASE WHEN date >= %s AND amount < 0 THEN -amount ELSE 0 END), 0)::float AS current_month,
                        COALESCE(SUM(CASE WHEN date >= %s AND date <= %s AND amount < 0 THEN -amount ELSE 0 END), 0)::float AS prev_month
                    FROM (
                        SELECT bt.amount::float, bt.booking_date AS date
                        FROM bank_transactions bt

                        UNION ALL

                        SELECT ct.amount::float, ct.booking_date AS date
                        FROM cash_transactions ct
                        LEFT JOIN receipt_cash_links rcl ON rcl.cash_transaction_id = ct.id
                        WHERE rcl.cash_transaction_id IS NULL
                    ) t
                    WHERE date >= %s
                    """,
                    (
                        first_this_month.isoformat(),
                        first_last_month.isoformat(),
                        last_month_end.isoformat(),
                        first_last_month.isoformat(),
                    ),
                )
                mom_row = cur.fetchone()
                current = float(mom_row[0]) if mom_row else 0.0
                previous = float(mom_row[1]) if mom_row else 0.0
                if previous > 0:
                    change_pct = round((current - previous) / previous * 100, 1)
                else:
                    change_pct = 0.0

                month_over_month = MonthOverMonth(
                    current=current, previous=previous, change_pct=change_pct
                )

            return AnalyticsSummary(
                total_expense=total_expense,
                total_income=total_income,
                transaction_count=transaction_count,
                monthly_totals=monthly_totals,
                by_category_group=by_category_group,
                by_vendor=by_vendor,
                by_category=by_category,
                month_over_month=month_over_month,
            )
        except Exception as e:
            print(f"UnifiedTransactionsRepository.get_analytics error: {e}")
            import traceback; traceback.print_exc()
            return _empty_analytics()


def _empty_analytics() -> AnalyticsSummary:
    return AnalyticsSummary(
        total_expense=0,
        total_income=0,
        transaction_count=0,
        monthly_totals=[],
        by_category_group=[],
        by_vendor=[],
        by_category=[],
        month_over_month=MonthOverMonth(current=0, previous=0, change_pct=0),
    )
