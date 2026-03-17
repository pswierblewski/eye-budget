"""
Repository for budget analysis: category breakdowns, classifications, financial focus,
recurring expenses, and cyclical alerts.
"""
from __future__ import annotations

import datetime
from typing import Optional


ESSENTIAL_KEYWORDS = [
    "kredyt", "hipoteka", "czynsz", "najem", "prąd", "gaz", "woda",
    "internet", "telefon", "ubezpieczenie", "podatek", "zus", "transport",
    "paliwo", "lekarstwo", "leczenie", "szkoła", "przedszkole",
]
DISCRETIONARY_KEYWORDS = [
    "restauracja", "kawiarnia", "rozrywka", "hobby", "ubrania", "kosmetyki",
    "elektronika", "podróże", "wakacje", "sport", "gry", "streaming",
    "alkohol", "prezenty",
]


def _classify_by_keyword(category_name: str) -> str:
    name_lower = category_name.lower()
    for kw in ESSENTIAL_KEYWORDS:
        if kw in name_lower:
            return "essential"
    for kw in DISCRETIONARY_KEYWORDS:
        if kw in name_lower:
            return "discretionary"
    return "discretionary"


class BudgetAnalysisRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    def dispose(self):
        pass

    # ------------------------------------------------------------------
    # Monthly category breakdown
    # ------------------------------------------------------------------

    def get_monthly_category_breakdown(self, year: int, month: int) -> list[dict]:
        """
        Returns per-category spending for target month and prior month in one query.
        Uses UNION of bank_transactions + cash_transactions (expenses only, amount < 0).
        """
        if not self.conn:
            return []
        try:
            # Calculate prior month
            if month == 1:
                prev_year, prev_month = year - 1, 12
            else:
                prev_year, prev_month = year, month - 1

            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    WITH txns AS (
                        SELECT category_id, amount, booking_date
                        FROM bank_transactions
                        WHERE amount < 0 AND category_id IS NOT NULL
                        UNION ALL
                        SELECT category_id, amount, booking_date
                        FROM cash_transactions
                        WHERE amount < 0 AND category_id IS NOT NULL
                    ),
                    current_month AS (
                        SELECT
                            t.category_id,
                            c.name AS category_name,
                            ABS(SUM(t.amount)) AS total_pln
                        FROM txns t
                        JOIN categories c ON c.id = t.category_id
                        WHERE EXTRACT(YEAR FROM t.booking_date) = %s
                          AND EXTRACT(MONTH FROM t.booking_date) = %s
                        GROUP BY t.category_id, c.name
                    ),
                    prev_month AS (
                        SELECT
                            t.category_id,
                            ABS(SUM(t.amount)) AS total_pln
                        FROM txns t
                        WHERE EXTRACT(YEAR FROM t.booking_date) = %s
                          AND EXTRACT(MONTH FROM t.booking_date) = %s
                        GROUP BY t.category_id
                    )
                    SELECT
                        cm.category_id,
                        cm.category_name,
                        cm.total_pln,
                        COALESCE(pm.total_pln, 0) AS prev_month_pln,
                        COALESCE(bcc.classification, 'discretionary') AS classification
                    FROM current_month cm
                    LEFT JOIN prev_month pm ON pm.category_id = cm.category_id
                    LEFT JOIN budget_category_classifications bcc ON bcc.category_id = cm.category_id
                    ORDER BY cm.total_pln DESC
                    """,
                    (year, month, prev_year, prev_month),
                )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_monthly_category_breakdown error: {e}")
            return []

    def get_monthly_totals(self, year: int, month: int) -> dict:
        """Returns income/expense totals for the given month."""
        if not self.conn:
            return {"income_pln": 0.0, "expenses_pln": 0.0}
        try:
            if month == 1:
                prev_year, prev_month = year - 1, 12
            else:
                prev_year, prev_month = year, month - 1
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    WITH txns AS (
                        SELECT amount, booking_date FROM bank_transactions
                        UNION ALL
                        SELECT amount, booking_date FROM cash_transactions
                    )
                    SELECT
                        COALESCE(SUM(CASE WHEN amount > 0 AND EXTRACT(YEAR FROM booking_date) = %s AND EXTRACT(MONTH FROM booking_date) = %s THEN amount ELSE 0 END), 0) AS income_pln,
                        COALESCE(SUM(CASE WHEN amount < 0 AND EXTRACT(YEAR FROM booking_date) = %s AND EXTRACT(MONTH FROM booking_date) = %s THEN ABS(amount) ELSE 0 END), 0) AS expenses_pln,
                        COALESCE(SUM(CASE WHEN amount < 0 AND EXTRACT(YEAR FROM booking_date) = %s AND EXTRACT(MONTH FROM booking_date) = %s THEN ABS(amount) ELSE 0 END), 0) AS prev_expenses_pln
                    FROM txns
                    """,
                    (year, month, year, month, prev_year, prev_month),
                )
                row = cur.fetchone()
                if row:
                    return {
                        "income_pln": float(row[0]),
                        "expenses_pln": float(row[1]),
                        "prev_expenses_pln": float(row[2]),
                    }
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_monthly_totals error: {e}")
        return {"income_pln": 0.0, "expenses_pln": 0.0, "prev_expenses_pln": 0.0}

    # ------------------------------------------------------------------
    # Category classifications
    # ------------------------------------------------------------------

    def get_all_classifications(self) -> list[dict]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bcc.category_id, c.name AS category_name,
                           bcc.classification, bcc.is_user_override
                    FROM budget_category_classifications bcc
                    JOIN categories c ON c.id = bcc.category_id
                    ORDER BY c.name
                    """
                )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_all_classifications error: {e}")
            return []

    def get_all_category_ids(self) -> list[dict]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT id, name FROM categories WHERE parent_id IS NOT NULL ORDER BY name")
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_all_category_ids error: {e}")
            return []

    def get_classified_category_ids(self) -> set[int]:
        if not self.conn:
            return set()
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT category_id FROM budget_category_classifications")
                return {row[0] for row in cur.fetchall()}
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_classified_category_ids error: {e}")
            return set()

    def upsert_classification(
        self, category_id: int, classification: str, is_user_override: bool
    ) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO budget_category_classifications
                        (category_id, classification, is_user_override, updated_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (category_id) DO UPDATE
                        SET classification = EXCLUDED.classification,
                            is_user_override = EXCLUDED.is_user_override,
                            updated_at = NOW()
                    """,
                    (category_id, classification, is_user_override),
                )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"BudgetAnalysisRepository.upsert_classification error: {e}")
            self.conn.rollback()
            return False

    def get_classification_by_category(self, category_id: int) -> Optional[dict]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT bcc.category_id, c.name AS category_name,
                           bcc.classification, bcc.is_user_override
                    FROM budget_category_classifications bcc
                    JOIN categories c ON c.id = bcc.category_id
                    WHERE bcc.category_id = %s
                    """,
                    (category_id,),
                )
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_classification_by_category error: {e}")
        return None

    # ------------------------------------------------------------------
    # Financial focus
    # ------------------------------------------------------------------

    def get_financial_focus(self) -> Optional[dict]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT id, label, description, is_active FROM budget_financial_focus WHERE is_active = TRUE LIMIT 1"
                )
                row = cur.fetchone()
                if row:
                    return {"id": row[0], "label": row[1], "description": row[2], "is_active": row[3]}
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_financial_focus error: {e}")
        return None

    def set_financial_focus(self, label: str, description: Optional[str]) -> Optional[dict]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE budget_financial_focus SET is_active = FALSE, updated_at = NOW()"
                )
                cur.execute(
                    """
                    INSERT INTO budget_financial_focus (label, description, is_active)
                    VALUES (%s, %s, TRUE)
                    RETURNING id, label, description, is_active
                    """,
                    (label, description),
                )
                row = cur.fetchone()
            self.conn.commit()
            if row:
                return {"id": row[0], "label": row[1], "description": row[2], "is_active": row[3]}
        except Exception as e:
            print(f"BudgetAnalysisRepository.set_financial_focus error: {e}")
            self.conn.rollback()
        return None

    # ------------------------------------------------------------------
    # Recurring expenses & cyclical alerts
    # ------------------------------------------------------------------

    def get_recurring_expenses(self) -> list[dict]:
        """Detect recurring and annual expenses via SQL heuristic."""
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    WITH txns AS (
                        SELECT
                            COALESCE(v.name, bt.description) AS vendor_name,
                            c.name AS category_name,
                            ABS(bt.amount) AS amount,
                            bt.booking_date
                        FROM bank_transactions bt
                        LEFT JOIN vendors v ON v.id = bt.vendor_id
                        LEFT JOIN categories c ON c.id = bt.category_id
                        WHERE bt.amount < 0
                        UNION ALL
                        SELECT
                            COALESCE(v.name, ct.description) AS vendor_name,
                            c.name AS category_name,
                            ABS(ct.amount) AS amount,
                            ct.booking_date
                        FROM cash_transactions ct
                        LEFT JOIN vendors v ON v.id = ct.vendor_id
                        LEFT JOIN categories c ON c.id = ct.category_id
                        WHERE ct.amount < 0
                    ),
                    grouped AS (
                        SELECT
                            vendor_name,
                            MAX(category_name) AS category_name,
                            COUNT(*) AS occurrence_count,
                            MIN(booking_date) AS first_date,
                            MAX(booking_date) AS last_date,
                            AVG(amount) AS avg_amount,
                            MIN(amount) AS min_amount,
                            MAX(amount) AS max_amount,
                            STDDEV(amount) AS stddev_amount,
                            ARRAY_AGG(booking_date ORDER BY booking_date) AS dates
                        FROM txns
                        WHERE vendor_name IS NOT NULL AND vendor_name != ''
                        GROUP BY vendor_name
                        HAVING COUNT(*) >= 2
                    )
                    SELECT
                        vendor_name,
                        category_name,
                        occurrence_count,
                        avg_amount,
                        min_amount,
                        max_amount,
                        stddev_amount,
                        last_date,
                        dates,
                        EXTRACT(YEAR FROM first_date) AS first_year,
                        EXTRACT(YEAR FROM last_date) AS last_year
                    FROM grouped
                    """
                )
                columns = [desc[0] for desc in cur.description]
                rows = [dict(zip(columns, row)) for row in cur.fetchall()]

            results = []
            for row in rows:
                dates = sorted(row["dates"])
                if len(dates) < 2:
                    continue
                # Compute intervals in days
                intervals = [
                    (dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)
                ]
                median_interval = sorted(intervals)[len(intervals) // 2]
                avg_amount = float(row["avg_amount"])
                stddev = float(row["stddev_amount"] or 0)
                occurrence_count = row["occurrence_count"]

                # Monthly recurring: 25-35 day interval, >=3 occurrences, stddev <= 20% of mean
                is_monthly = (
                    occurrence_count >= 3
                    and 25 <= median_interval <= 35
                    and (stddev <= 0.2 * avg_amount if avg_amount > 0 else True)
                )
                # Annual cyclical: 300-400 day interval, >=2 occurrences, different years
                is_annual = (
                    occurrence_count >= 2
                    and 300 <= median_interval <= 400
                    and row["first_year"] != row["last_year"]
                )

                if not (is_monthly or is_annual):
                    continue

                last_date = row["last_date"]
                if isinstance(last_date, datetime.date):
                    next_expected = last_date + datetime.timedelta(days=median_interval)
                else:
                    next_expected = datetime.date.today()

                results.append({
                    "vendor_name": row["vendor_name"],
                    "category_name": row["category_name"],
                    "frequency": "monthly" if is_monthly else "annual",
                    "avg_amount_pln": avg_amount,
                    "last_occurrence_date": last_date.isoformat() if isinstance(last_date, datetime.date) else str(last_date),
                    "next_expected_date": next_expected.isoformat(),
                    "amount_min_pln": float(row["min_amount"]),
                    "amount_max_pln": float(row["max_amount"]),
                    "occurrence_count": occurrence_count,
                    "median_interval": median_interval,
                })

            return results
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_recurring_expenses error: {e}")
            return []

    def get_cyclical_alerts(self, days_ahead: int = 90) -> list[dict]:
        """Returns annual recurring expenses due within days_ahead days."""
        recurring = self.get_recurring_expenses()
        today = datetime.date.today()
        cutoff = today + datetime.timedelta(days=days_ahead)
        alerts = []
        for item in recurring:
            if item["frequency"] != "annual":
                continue
            try:
                next_date = datetime.date.fromisoformat(item["next_expected_date"])
            except Exception:
                continue
            if today <= next_date <= cutoff:
                days_until = (next_date - today).days
                avg = item["avg_amount_pln"]
                min_a = item["amount_min_pln"]
                max_a = item["amount_max_pln"]
                alerts.append({
                    "vendor_name": item["vendor_name"],
                    "category_name": item["category_name"],
                    "next_expected_date": item["next_expected_date"],
                    "days_until": days_until,
                    "expected_amount_pln": avg,
                    "amount_range_pln": f"{min_a:.0f}–{max_a:.0f} PLN",
                })
        alerts.sort(key=lambda x: x["days_until"])
        return alerts

    # ------------------------------------------------------------------
    # Current month income/expenses (for affordability check)
    # ------------------------------------------------------------------

    def get_current_month_income_and_expenses(self) -> dict:
        today = datetime.date.today()
        year, month = today.year, today.month
        if not self.conn:
            return {"income_pln": 0.0, "expenses_pln": 0.0, "upcoming_recurring_sum_30d": 0.0}
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    WITH txns AS (
                        SELECT amount, booking_date FROM bank_transactions
                        UNION ALL
                        SELECT amount, booking_date FROM cash_transactions
                    )
                    SELECT
                        COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0) AS income_pln,
                        COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0) AS expenses_pln
                    FROM txns
                    WHERE EXTRACT(YEAR FROM booking_date) = %s
                      AND EXTRACT(MONTH FROM booking_date) = %s
                    """,
                    (year, month),
                )
                row = cur.fetchone()
                income_pln = float(row[0]) if row else 0.0
                expenses_pln = float(row[1]) if row else 0.0
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_current_month_income_and_expenses error: {e}")
            income_pln, expenses_pln = 0.0, 0.0

        # Sum recurring monthly expenses expected in next 30 days
        recurring = self.get_recurring_expenses()
        cutoff = datetime.date.today() + datetime.timedelta(days=30)
        upcoming_sum = 0.0
        for item in recurring:
            if item["frequency"] != "monthly":
                continue
            try:
                next_date = datetime.date.fromisoformat(item["next_expected_date"])
                if datetime.date.today() <= next_date <= cutoff:
                    upcoming_sum += item["avg_amount_pln"]
            except Exception:
                pass

        return {
            "income_pln": income_pln,
            "expenses_pln": expenses_pln,
            "upcoming_recurring_sum_30d": upcoming_sum,
        }

    # ------------------------------------------------------------------
    # 3-month rolling averages (used by goals surplus + simulation)
    # ------------------------------------------------------------------

    def get_rolling_3month_averages(self) -> dict:
        """Returns avg income and expenses over the last 3 complete months."""
        if not self.conn:
            return {"avg_income": 0.0, "avg_expenses": 0.0}
        try:
            today = datetime.date.today()
            # Build list of last 3 complete months
            months = []
            y, m = today.year, today.month
            for _ in range(3):
                if m == 1:
                    y -= 1
                    m = 12
                else:
                    m -= 1
                months.append((y, m))

            totals_income = []
            totals_expenses = []
            with self.conn.cursor() as cur:
                for my, mm in months:
                    cur.execute(
                        """
                        WITH txns AS (
                            SELECT amount, booking_date FROM bank_transactions
                            UNION ALL
                            SELECT amount, booking_date FROM cash_transactions
                        )
                        SELECT
                            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0),
                            COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0)
                        FROM txns
                        WHERE EXTRACT(YEAR FROM booking_date) = %s
                          AND EXTRACT(MONTH FROM booking_date) = %s
                        """,
                        (my, mm),
                    )
                    row = cur.fetchone()
                    if row:
                        totals_income.append(float(row[0]))
                        totals_expenses.append(float(row[1]))

            avg_income = sum(totals_income) / len(totals_income) if totals_income else 0.0
            avg_expenses = sum(totals_expenses) / len(totals_expenses) if totals_expenses else 0.0
            return {"avg_income": avg_income, "avg_expenses": avg_expenses}
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_rolling_3month_averages error: {e}")
            return {"avg_income": 0.0, "avg_expenses": 0.0}

    def get_monthly_history(self, months_count: int = 3) -> list[dict]:
        """Returns monthly income/expense breakdown for the last N complete months."""
        if not self.conn:
            return []
        today = datetime.date.today()
        months = []
        y, m = today.year, today.month
        for _ in range(months_count):
            if m == 1:
                y -= 1
                m = 12
            else:
                m -= 1
            months.append((y, m))

        result = []
        try:
            with self.conn.cursor() as cur:
                for my, mm in months:
                    cur.execute(
                        """
                        WITH txns AS (
                            SELECT amount, booking_date FROM bank_transactions
                            UNION ALL
                            SELECT amount, booking_date FROM cash_transactions
                        )
                        SELECT
                            COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END), 0),
                            COALESCE(SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END), 0)
                        FROM txns
                        WHERE EXTRACT(YEAR FROM booking_date) = %s
                          AND EXTRACT(MONTH FROM booking_date) = %s
                        """,
                        (my, mm),
                    )
                    row = cur.fetchone()
                    income = float(row[0]) if row else 0.0
                    expenses = float(row[1]) if row else 0.0
                    result.append({
                        "year": my,
                        "month": mm,
                        "income_pln": income,
                        "expenses_pln": expenses,
                        "surplus_pln": income - expenses,
                    })
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_monthly_history error: {e}")
        return result

    def count_distinct_months(self) -> int:
        """Count distinct year-month combinations with at least one transaction."""
        if not self.conn:
            return 0
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(DISTINCT TO_CHAR(booking_date, 'YYYY-MM')) FROM (
                        SELECT booking_date FROM bank_transactions
                        UNION ALL
                        SELECT booking_date FROM cash_transactions
                    ) t
                    """
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            print(f"BudgetAnalysisRepository.count_distinct_months error: {e}")
            return 0

    # ------------------------------------------------------------------
    # Emergency advisor: discretionary category averages
    # ------------------------------------------------------------------

    def get_discretionary_category_averages(self) -> list[dict]:
        """Returns average monthly spending per discretionary category (last 3 months)."""
        if not self.conn:
            return []
        try:
            today = datetime.date.today()
            cutoff = today - datetime.timedelta(days=90)
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    WITH txns AS (
                        SELECT category_id, ABS(amount) AS amount, booking_date
                        FROM bank_transactions
                        WHERE amount < 0 AND category_id IS NOT NULL
                          AND booking_date >= %s
                        UNION ALL
                        SELECT category_id, ABS(amount) AS amount, booking_date
                        FROM cash_transactions
                        WHERE amount < 0 AND category_id IS NOT NULL
                          AND booking_date >= %s
                    )
                    SELECT
                        c.name AS category_name,
                        AVG(monthly_total) AS avg_monthly_spend_pln
                    FROM (
                        SELECT
                            t.category_id,
                            DATE_TRUNC('month', t.booking_date) AS month,
                            SUM(t.amount) AS monthly_total
                        FROM txns t
                        GROUP BY t.category_id, DATE_TRUNC('month', t.booking_date)
                    ) monthly
                    JOIN categories c ON c.id = monthly.category_id
                    JOIN budget_category_classifications bcc ON bcc.category_id = monthly.category_id
                    WHERE bcc.classification = 'discretionary'
                    GROUP BY c.name
                    HAVING AVG(monthly_total) > 0
                    ORDER BY avg_monthly_spend_pln DESC
                    """,
                    (cutoff, cutoff),
                )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as e:
            print(f"BudgetAnalysisRepository.get_discretionary_category_averages error: {e}")
            return []
