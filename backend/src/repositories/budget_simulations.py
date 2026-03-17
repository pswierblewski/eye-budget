"""
Repository for budget_simulations and budget_ai_recommendations tables.
"""
from __future__ import annotations

import datetime
import json
from typing import Optional


class BudgetSimulationsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    def dispose(self):
        pass

    # ------------------------------------------------------------------
    # Simulations
    # ------------------------------------------------------------------

    def create_simulation(
        self,
        name: str,
        expense_name: str,
        amount: float,
        expense_type: str,
        start_date: str,
    ) -> Optional[dict]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO budget_simulations
                        (name, expense_name, expense_amount, expense_type, expense_start_date, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    RETURNING id, name, expense_name, expense_amount, expense_type,
                              expense_start_date, status, result_json, error_message, created_at
                    """,
                    (name, expense_name, amount, expense_type, start_date),
                )
                row = cur.fetchone()
            self.conn.commit()
            if row:
                return self._row_to_dict(row)
        except Exception as e:
            print(f"BudgetSimulationsRepository.create_simulation error: {e}")
            self.conn.rollback()
        return None

    def get_simulation(self, sim_id: int) -> Optional[dict]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, expense_name, expense_amount, expense_type,
                           expense_start_date, status, result_json, error_message, created_at
                    FROM budget_simulations WHERE id = %s
                    """,
                    (sim_id,),
                )
                row = cur.fetchone()
                if row:
                    return self._row_to_dict(row)
        except Exception as e:
            print(f"BudgetSimulationsRepository.get_simulation error: {e}")
        return None

    def get_all_simulations(self) -> list[dict]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, expense_name, expense_amount, expense_type,
                           expense_start_date, status, result_json, error_message, created_at
                    FROM budget_simulations
                    ORDER BY created_at DESC
                    """
                )
                return [self._row_to_dict(row) for row in cur.fetchall()]
        except Exception as e:
            print(f"BudgetSimulationsRepository.get_all_simulations error: {e}")
            return []

    def update_simulation_status(
        self,
        sim_id: int,
        status: str,
        result_json: Optional[dict] = None,
        error: Optional[str] = None,
    ) -> None:
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE budget_simulations
                    SET status = %s,
                        result_json = %s,
                        error_message = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (
                        status,
                        json.dumps(result_json) if result_json is not None else None,
                        error,
                        sim_id,
                    ),
                )
            self.conn.commit()
        except Exception as e:
            print(f"BudgetSimulationsRepository.update_simulation_status error: {e}")
            self.conn.rollback()

    def delete_simulation(self, sim_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM budget_simulations WHERE id = %s", (sim_id,))
                affected = cur.rowcount
            self.conn.commit()
            return affected > 0
        except Exception as e:
            print(f"BudgetSimulationsRepository.delete_simulation error: {e}")
            self.conn.rollback()
            return False

    def _row_to_dict(self, row) -> dict:
        keys = ["id", "name", "expense_name", "expense_amount", "expense_type",
                "expense_start_date", "status", "result_json", "error_message", "created_at"]
        d = dict(zip(keys, row))
        if isinstance(d.get("expense_start_date"), datetime.date):
            d["expense_start_date"] = d["expense_start_date"].isoformat()
        if isinstance(d.get("created_at"), (datetime.datetime, datetime.date)):
            d["created_at"] = d["created_at"].isoformat()
        if d.get("expense_amount") is not None:
            d["expense_amount"] = float(d["expense_amount"])
        return d

    # ------------------------------------------------------------------
    # AI recommendations
    # ------------------------------------------------------------------

    def get_current_recommendations(self) -> Optional[dict]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, generated_at, data_through_date,
                           recommendations_json, is_current, months_of_data
                    FROM budget_ai_recommendations
                    WHERE is_current = TRUE
                    ORDER BY generated_at DESC
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "generated_at": row[1].isoformat() if row[1] else None,
                        "data_through_date": row[2].isoformat() if isinstance(row[2], datetime.date) else str(row[2]) if row[2] else None,
                        "recommendations_json": row[3] if row[3] else [],
                        "is_current": row[4],
                        "months_of_data": row[5],
                    }
        except Exception as e:
            print(f"BudgetSimulationsRepository.get_current_recommendations error: {e}")
        return None

    def save_recommendations(
        self,
        insights_json: list,
        data_through_date: str,
        months_of_data: int,
    ) -> None:
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE budget_ai_recommendations SET is_current = FALSE"
                )
                cur.execute(
                    """
                    INSERT INTO budget_ai_recommendations
                        (data_through_date, recommendations_json, is_current, months_of_data)
                    VALUES (%s, %s, TRUE, %s)
                    """,
                    (data_through_date, json.dumps(insights_json), months_of_data),
                )
            self.conn.commit()
        except Exception as e:
            print(f"BudgetSimulationsRepository.save_recommendations error: {e}")
            self.conn.rollback()
