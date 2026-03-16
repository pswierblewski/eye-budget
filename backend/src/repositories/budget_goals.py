"""
Repository for budget_financial_goals table.
"""
from __future__ import annotations

from typing import Optional


class BudgetGoalsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    def dispose(self):
        pass

    def get_all_goals(self) -> list[dict]:
        if not self.conn:
            return []
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, target_amount, target_date, priority_rank,
                           monthly_allocation_amount, accumulated_progress, is_active,
                           created_at, updated_at
                    FROM budget_financial_goals
                    WHERE is_active = TRUE
                    ORDER BY priority_rank, id
                    """
                )
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
        except Exception as e:
            print(f"BudgetGoalsRepository.get_all_goals error: {e}")
            return []

    def get_goal(self, goal_id: int) -> Optional[dict]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, name, target_amount, target_date, priority_rank,
                           monthly_allocation_amount, accumulated_progress, is_active,
                           created_at, updated_at
                    FROM budget_financial_goals WHERE id = %s
                    """,
                    (goal_id,),
                )
                row = cur.fetchone()
                if row:
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, row))
        except Exception as e:
            print(f"BudgetGoalsRepository.get_goal error: {e}")
        return None

    def create_goal(
        self,
        name: str,
        target_amount: float,
        target_date: Optional[str],
        priority_rank: int,
        monthly_allocation: float,
    ) -> Optional[dict]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO budget_financial_goals
                        (name, target_amount, target_date, priority_rank, monthly_allocation_amount)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, name, target_amount, target_date, priority_rank,
                              monthly_allocation_amount, accumulated_progress, is_active,
                              created_at, updated_at
                    """,
                    (name, target_amount, target_date, priority_rank, monthly_allocation),
                )
                row = cur.fetchone()
            self.conn.commit()
            if row:
                columns = ["id", "name", "target_amount", "target_date", "priority_rank",
                           "monthly_allocation_amount", "accumulated_progress", "is_active",
                           "created_at", "updated_at"]
                return dict(zip(columns, row))
        except Exception as e:
            print(f"BudgetGoalsRepository.create_goal error: {e}")
            self.conn.rollback()
        return None

    def update_goal(self, goal_id: int, **fields) -> Optional[dict]:
        if not self.conn or not fields:
            return self.get_goal(goal_id)
        # Map frontend field names to DB column names
        column_map = {
            "name": "name",
            "target_amount_pln": "target_amount",
            "target_date": "target_date",
            "priority_rank": "priority_rank",
            "monthly_allocation_amount_pln": "monthly_allocation_amount",
            "is_active": "is_active",
        }
        set_clauses = []
        values = []
        for key, val in fields.items():
            col = column_map.get(key, key)
            set_clauses.append(f"{col} = %s")
            values.append(val)
        set_clauses.append("updated_at = NOW()")
        values.append(goal_id)
        sql = f"UPDATE budget_financial_goals SET {', '.join(set_clauses)} WHERE id = %s"
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, values)
            self.conn.commit()
            return self.get_goal(goal_id)
        except Exception as e:
            print(f"BudgetGoalsRepository.update_goal error: {e}")
            self.conn.rollback()
        return None

    def soft_delete_goal(self, goal_id: int) -> bool:
        if not self.conn:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "UPDATE budget_financial_goals SET is_active = FALSE, updated_at = NOW() WHERE id = %s",
                    (goal_id,),
                )
                affected = cur.rowcount
            self.conn.commit()
            return affected > 0
        except Exception as e:
            print(f"BudgetGoalsRepository.soft_delete_goal error: {e}")
            self.conn.rollback()
            return False

    def get_active_goal_allocations_total(self) -> float:
        if not self.conn:
            return 0.0
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    "SELECT COALESCE(SUM(monthly_allocation_amount), 0) FROM budget_financial_goals WHERE is_active = TRUE"
                )
                row = cur.fetchone()
                return float(row[0]) if row else 0.0
        except Exception as e:
            print(f"BudgetGoalsRepository.get_active_goal_allocations_total error: {e}")
            return 0.0

    def advance_monthly_progress_for_all_active_goals(self) -> None:
        if not self.conn:
            return
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE budget_financial_goals
                    SET accumulated_progress = LEAST(
                            accumulated_progress + monthly_allocation_amount,
                            target_amount
                        ),
                        updated_at = NOW()
                    WHERE is_active = TRUE AND monthly_allocation_amount > 0
                    """
                )
            self.conn.commit()
        except Exception as e:
            print(f"BudgetGoalsRepository.advance_monthly_progress_for_all_active_goals error: {e}")
            self.conn.rollback()
