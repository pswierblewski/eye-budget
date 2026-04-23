"""
Repository for settlement_groups and settlement_group_members.
"""
from __future__ import annotations

import datetime
import logging
from decimal import Decimal
from typing import Any, Optional

import psycopg2
import psycopg2.errors

logger = logging.getLogger(__name__)

from ..data import (
    LinkedReceiptSummary,
    SettlementGroupDetail,
    SettlementGroupMemberRef,
    SettlementMemberRow,
)


def _row_ts(val: Any) -> str:
    if isinstance(val, datetime.datetime):
        return val.isoformat()
    if isinstance(val, datetime.date):
        return val.isoformat()
    return str(val) if val else ""


def _row_dt(val: Any) -> str:
    if isinstance(val, datetime.datetime):
        return val.date().isoformat() if val else ""
    if isinstance(val, datetime.date):
        return val.isoformat()
    return str(val) if val else ""


def _to_decimal(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


class SettlementGroupsRepository:
    def __init__(self, db_context):
        self.conn = db_context.conn

    def dispose(self) -> None:
        pass

    def create_group(
        self,
        title: Optional[str],
        note: Optional[str],
        members: list[SettlementGroupMemberRef] | list[dict[str, Any]],
    ) -> int:
        """Create a group and optional members in one transaction. Returns group id."""
        if not self.conn:
            raise RuntimeError("No database connection")
        seen: set[tuple[str, int]] = set()
        to_insert: list[tuple[str, int]] = []
        for m in members:
            if isinstance(m, SettlementGroupMemberRef):
                st, mid = m.source_type, m.id
            else:
                st, mid = m["source_type"], m["id"]
            key = (st, int(mid))
            if key in seen:
                continue
            seen.add(key)
            to_insert.append((st, int(mid)))
        with self.conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    INSERT INTO settlement_groups (title, note)
                    VALUES (%s, %s)
                    RETURNING id
                    """,
                    (title, note),
                )
                row = cur.fetchone()
                if not row:
                    raise RuntimeError("Failed to create settlement group")
                gid = int(row[0])
                for st, tid in to_insert:
                    if st == "bank":
                        cur.execute(
                            """
                            INSERT INTO settlement_group_members (group_id, bank_transaction_id)
                            VALUES (%s, %s)
                            """,
                            (gid, tid),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO settlement_group_members (group_id, cash_transaction_id)
                            VALUES (%s, %s)
                            """,
                            (gid, tid),
                        )
                self.conn.commit()
            except (psycopg2.errors.ForeignKeyViolation, psycopg2.errors.UniqueViolation) as e:
                self.conn.rollback()
                raise e
        return gid

    def get_group_id_for_transaction(
        self, source_type: str, transaction_id: int
    ) -> int | None:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                if source_type == "bank":
                    cur.execute(
                        """
                        SELECT group_id FROM settlement_group_members
                        WHERE bank_transaction_id = %s
                        """,
                        (transaction_id,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT group_id FROM settlement_group_members
                        WHERE cash_transaction_id = %s
                        """,
                        (transaction_id,),
                    )
                r = cur.fetchone()
                return int(r[0]) if r else None
        except Exception:
            logger.exception("get_group_id_for_transaction failed")
            raise

    def get_list(
        self,
        search: str | None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "created_at",
        sort_dir: str = "desc",
    ) -> tuple[list[dict[str, Any]], int]:
        if not self.conn:
            return [], 0
        sort_cols = {
            "created_at": "sg.created_at",
            "title": "sg.title",
            "id": "sg.id",
        }
        order_expr = sort_cols.get(sort_by, "sg.created_at")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
        order_clause = f"{order_expr} {direction} NULLS LAST, sg.id DESC"
        conditions: list[str] = []
        params: list = []
        if search:
            conditions.append(
                "(sg.title ILIKE %s OR COALESCE(sg.note, '') ILIKE %s)"
            )
            p = f"%{search}%"
            params.extend([p, p])
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        sg.id, sg.title, sg.note, sg.created_at, sg.updated_at,
                        (SELECT COUNT(*)::int
                         FROM settlement_group_members sgm2
                         WHERE sgm2.group_id = sg.id) AS member_count,
                        COUNT(*) OVER () AS total_count
                    FROM settlement_groups sg
                    {where}
                    ORDER BY {order_clause}
                    LIMIT %s OFFSET %s
                    """,
                    params + [limit, offset],
                )
                rows = cur.fetchall()
            if not rows:
                return [], 0
            total = int(rows[0][-1])
            items: list[dict[str, Any]] = []
            for r in rows:
                items.append(
                    {
                        "id": r[0],
                        "title": r[1],
                        "note": r[2],
                        "created_at": _row_ts(r[3]),
                        "updated_at": _row_ts(r[4]) if r[4] else None,
                        "member_count": r[5],
                    }
                )
            return items, total
        except Exception:
            logger.exception("get_list failed")
            raise

    def _member_rows_for_group(
        self, cur: Any, group_id: int
    ) -> tuple[list[SettlementMemberRow], list[float]]:
        cur.execute(
            """
            SELECT
                CASE WHEN sgm.bank_transaction_id IS NOT NULL THEN 'bank' ELSE 'cash' END,
                COALESCE(sgm.bank_transaction_id, sgm.cash_transaction_id),
                COALESCE(bt.booking_date, ct.booking_date),
                COALESCE(bt.amount, ct.amount)::float,
                COALESCE(bt.description, ct.description, bt.counterparty, ''),
                v.name,
                COALESCE(bt.currency, ct.currency, 'PLN')
            FROM settlement_group_members sgm
            LEFT JOIN bank_transactions bt ON bt.id = sgm.bank_transaction_id
            LEFT JOIN cash_transactions ct ON ct.id = sgm.cash_transaction_id
            LEFT JOIN vendors v ON v.id = COALESCE(bt.vendor_id, ct.vendor_id)
            WHERE sgm.group_id = %s
            ORDER BY COALESCE(bt.booking_date, ct.booking_date) NULLS LAST, sgm.id
            """,
            (group_id,),
        )
        mrows: list[SettlementMemberRow] = []
        amounts: list[float] = []
        for s in cur.fetchall():
            amt = float(s[3]) if s[3] is not None else 0.0
            amounts.append(amt)
            mrows.append(
                SettlementMemberRow(
                    source_type=s[0],
                    id=int(s[1]),
                    booking_date=_row_dt(s[2]),
                    amount=amt,
                    description=(s[4] or None),
                    vendor_name=(s[5] or None),
                    currency=s[6] or "PLN",
                )
            )
        return mrows, amounts

    def _linked_receipts(self, cur: Any, group_id: int) -> list[LinkedReceiptSummary]:
        out: list[LinkedReceiptSummary] = []
        seen: set[int] = set()
        cur.execute(
            """
            SELECT DISTINCT rs.id, rs.filename, COALESCE(v.name, rt.raw_vendor_name)
            FROM settlement_group_members sgm
            INNER JOIN receipt_bank_links rbl ON rbl.bank_transaction_id = sgm.bank_transaction_id
            INNER JOIN receipt_transactions rt ON rt.id = rbl.receipt_transaction_id
            INNER JOIN receipts_scans rs ON rs.id = rt.scan_id
            LEFT JOIN vendors v ON v.id = rt.vendor_id
            WHERE sgm.group_id = %s
            """,
            (group_id,),
        )
        for r in cur.fetchall():
            scan_id = int(r[0])
            if scan_id in seen:
                continue
            seen.add(scan_id)
            out.append(
                LinkedReceiptSummary(
                    scan_id=scan_id,
                    filename=r[1],
                    vendor_name=(r[2] or None),
                )
            )
        cur.execute(
            """
            SELECT DISTINCT rs.id, rs.filename, COALESCE(v.name, rt.raw_vendor_name)
            FROM settlement_group_members sgm
            INNER JOIN receipt_cash_links rcl ON rcl.cash_transaction_id = sgm.cash_transaction_id
            INNER JOIN receipt_transactions rt ON rt.id = rcl.receipt_transaction_id
            INNER JOIN receipts_scans rs ON rs.id = rt.scan_id
            LEFT JOIN vendors v ON v.id = rt.vendor_id
            WHERE sgm.group_id = %s
            """,
            (group_id,),
        )
        for r in cur.fetchall():
            scan_id = int(r[0])
            if scan_id in seen:
                continue
            seen.add(scan_id)
            out.append(
                LinkedReceiptSummary(
                    scan_id=scan_id,
                    filename=r[1],
                    vendor_name=(r[2] or None),
                )
            )
        return out

    def get_by_id(self, group_id: int) -> Optional[SettlementGroupDetail]:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, note, created_at, updated_at
                    FROM settlement_groups
                    WHERE id = %s
                    """,
                    (group_id,),
                )
                g = cur.fetchone()
                if not g:
                    return None
                members, amounts = self._member_rows_for_group(cur, group_id)
                linked = self._linked_receipts(cur, group_id)
                member_count = len(members)
                total_income = sum(
                    _to_decimal(a) for a in amounts if a > 0
                )
                total_expense = sum(
                    -_to_decimal(a) for a in amounts if a < 0
                )
                net = sum((_to_decimal(a) for a in amounts), start=Decimal("0"))
            return SettlementGroupDetail(
                id=int(g[0]),
                title=g[1],
                note=g[2],
                created_at=_row_ts(g[3]) if g[3] else "",
                updated_at=_row_ts(g[4]) if g[4] else None,
                member_count=member_count,
                members=members,
                linked_receipts=linked,
                total_expense=total_expense,
                total_income=total_income,
                net=net,
            )
        except Exception:
            logger.exception("get_by_id failed")
            raise

    def move_member(
        self,
        from_group_id: int,
        to_group_id: int,
        source_type: str,
        transaction_id: int,
    ) -> bool:
        """Remove membership from from_group_id and add to to_group_id in one transaction."""
        if not self.conn:
            return False
        if from_group_id == to_group_id:
            return True
        with self.conn.cursor() as cur:
            try:
                if source_type == "bank":
                    cur.execute(
                        """
                        DELETE FROM settlement_group_members
                        WHERE group_id = %s AND bank_transaction_id = %s
                        """,
                        (from_group_id, transaction_id),
                    )
                    if cur.rowcount == 0:
                        self.conn.rollback()
                        return False
                    cur.execute(
                        """
                        INSERT INTO settlement_group_members (group_id, bank_transaction_id)
                        VALUES (%s, %s)
                        """,
                        (to_group_id, transaction_id),
                    )
                else:
                    cur.execute(
                        """
                        DELETE FROM settlement_group_members
                        WHERE group_id = %s AND cash_transaction_id = %s
                        """,
                        (from_group_id, transaction_id),
                    )
                    if cur.rowcount == 0:
                        self.conn.rollback()
                        return False
                    cur.execute(
                        """
                        INSERT INTO settlement_group_members (group_id, cash_transaction_id)
                        VALUES (%s, %s)
                        """,
                        (to_group_id, transaction_id),
                    )
                self.conn.commit()
                return True
            except (psycopg2.errors.UniqueViolation, psycopg2.errors.ForeignKeyViolation):
                self.conn.rollback()
                raise

    def add_member(
        self, group_id: int, source_type: str, transaction_id: int
    ) -> bool:
        if not self.conn:
            return False
        with self.conn.cursor() as cur:
            try:
                if source_type == "bank":
                    cur.execute(
                        """
                        INSERT INTO settlement_group_members (group_id, bank_transaction_id)
                        VALUES (%s, %s)
                        """,
                        (group_id, transaction_id),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO settlement_group_members (group_id, cash_transaction_id)
                        VALUES (%s, %s)
                        """,
                        (group_id, transaction_id),
                    )
                self.conn.commit()
                return True
            except (psycopg2.errors.UniqueViolation, psycopg2.errors.ForeignKeyViolation) as e:
                self.conn.rollback()
                raise e

    def remove_member(
        self, group_id: int, source_type: str, transaction_id: int
    ) -> bool:
        if not self.conn:
            return False
        with self.conn.cursor() as cur:
            if source_type == "bank":
                cur.execute(
                    """
                    DELETE FROM settlement_group_members
                    WHERE group_id = %s AND bank_transaction_id = %s
                    """,
                    (group_id, transaction_id),
                )
            else:
                cur.execute(
                    """
                    DELETE FROM settlement_group_members
                    WHERE group_id = %s AND cash_transaction_id = %s
                    """,
                    (group_id, transaction_id),
                )
            n = cur.rowcount
        self.conn.commit()
        return n > 0

    def update_group(self, group_id: int, updates: dict[str, Any]) -> bool:
        """Patch fields present in `updates` (typically title and/or note, including nulls)."""
        if not self.conn:
            return False
        allowed = ("title", "note")
        keys = [k for k in allowed if k in updates]
        if not keys:
            return True
        set_parts = [f"{k} = %s" for k in keys]
        vals = [updates[k] for k in keys] + [group_id]
        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE settlement_groups
                SET {", ".join(set_parts)}, updated_at = NOW()
                WHERE id = %s
                """,
                vals,
            )
            ok = cur.rowcount > 0
        self.conn.commit()
        return ok

    def delete_group(self, group_id: int) -> bool:
        if not self.conn:
            return False
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM settlement_groups WHERE id = %s", (group_id,))
            n = cur.rowcount
        self.conn.commit()
        return n > 0

