from abc import ABC
from psycopg2 import extras

from ..data import (
    EvaluationResult,
    EvaluationMetrics,
    EvaluationRunSummary,
    EvaluationRunListItem,
    EvaluationRunDetail,
    TransactionModel,
)


class EvaluationsRepository(ABC):
    def __init__(self, db_context):
        self.conn = db_context.conn

    def create_run(self, model_used: str, config: dict = None) -> int:
        """Create a new evaluation run and return its ID."""
        if not self.conn:
            print("No database connection available.")
            return -1
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO evaluation_runs 
                    (model_used, total_files, successful, failed, config)
                    VALUES (%s, 0, 0, 0, %s)
                    RETURNING id
                    """,
                    (model_used, extras.Json(config) if config else None)
                )
                run_id = cursor.fetchone()[0]
                self.conn.commit()
                print(f"Evaluation run {run_id} created.")
                return run_id
        except Exception as e:
            print("Failed to create evaluation run:", e)
            self.conn.rollback()
            return -1

    def add_result(self, run_id: int, result: EvaluationResult) -> bool:
        """Add an individual file result to an evaluation run."""
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                metrics = result.metrics
                cursor.execute(
                    """
                    INSERT INTO evaluation_results 
                    (run_id, filename, success, error_message, processing_time_ms,
                     fields_extracted, field_completeness, product_count,
                     has_vendor, has_date, has_total,
                     products_sum, extracted_total, total_difference, is_consistent,
                     result)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        run_id,
                        result.filename,
                        result.success,
                        result.error_message,
                        metrics.processing_time_ms if metrics else None,
                        metrics.fields_extracted if metrics else None,
                        metrics.field_completeness if metrics else None,
                        metrics.product_count if metrics else None,
                        metrics.has_vendor if metrics else None,
                        metrics.has_date if metrics else None,
                        metrics.has_total if metrics else None,
                        metrics.products_sum if metrics else None,
                        metrics.extracted_total if metrics else None,
                        metrics.total_difference if metrics else None,
                        metrics.is_consistent if metrics else None,
                        extras.Json(result.transaction.model_dump()) if result.transaction else None
                    )
                )
                self.conn.commit()
                return True
        except Exception as e:
            print(f"Failed to add evaluation result for {result.filename}:", e)
            self.conn.rollback()
            return False

    def update_run_summary(self, run_id: int, summary: EvaluationRunSummary) -> bool:
        """Update the evaluation run with summary statistics."""
        if not self.conn:
            print("No database connection available.")
            return False
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE evaluation_runs
                    SET total_files = %s,
                        successful = %s,
                        failed = %s,
                        success_rate = %s,
                        avg_processing_time_ms = %s,
                        avg_field_completeness = %s,
                        avg_consistency_rate = %s
                    WHERE id = %s
                    """,
                    (
                        summary.total_files,
                        summary.successful,
                        summary.failed,
                        summary.success_rate,
                        summary.avg_processing_time_ms,
                        summary.avg_field_completeness,
                        summary.avg_consistency_rate,
                        run_id
                    )
                )
                self.conn.commit()
                print(f"Evaluation run {run_id} summary updated.")
                return True
        except Exception as e:
            print("Failed to update evaluation run summary:", e)
            self.conn.rollback()
            return False

    def dispose(self):
        print("EvaluationsRepository disposed.")

    # ------------------------------------------------------------------
    # New methods for the evaluations list/detail API
    # ------------------------------------------------------------------

    def get_all_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "id",
        sort_dir: str = "desc",
    ) -> tuple[list[EvaluationRunListItem], int]:
        _SORT_COLS: dict[str, str] = {
            "id": "id",
            "run_timestamp": "run_timestamp",
            "model_used": "model_used",
            "total_files": "total_files",
            "success_rate": "success_rate",
            "avg_field_completeness": "avg_field_completeness",
            "avg_consistency_rate": "avg_consistency_rate",
            "avg_processing_time_ms": "avg_processing_time_ms",
        }
        order_expr = _SORT_COLS.get(sort_by, "id")
        direction = "ASC" if sort_dir.lower() == "asc" else "DESC"
        if not self.conn:
            return [], 0
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, run_timestamp, model_used, total_files, successful, failed,
                           success_rate, avg_processing_time_ms, avg_field_completeness,
                           avg_consistency_rate, config,
                           COUNT(*) OVER () AS total_count
                    FROM evaluation_runs
                    ORDER BY {order_expr} {direction} NULLS LAST
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cursor.fetchall()
                total = int(rows[0][11]) if rows else 0
                return [
                    EvaluationRunListItem(
                        id=r[0],
                        run_timestamp=r[1],
                        model_used=r[2],
                        total_files=r[3],
                        successful=r[4],
                        failed=r[5],
                        success_rate=float(r[6]) if r[6] is not None else None,
                        avg_processing_time_ms=float(r[7]) if r[7] is not None else None,
                        avg_field_completeness=float(r[8]) if r[8] is not None else None,
                        avg_consistency_rate=float(r[9]) if r[9] is not None else None,
                        config=r[10],
                    )
                    for r in rows
                ], total
        except Exception as e:
            print("Failed to fetch evaluation runs:", e)
            return [], 0

    def get_run_with_results(self, run_id: int) -> EvaluationRunDetail | None:
        if not self.conn:
            return None
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, run_timestamp, model_used, total_files, successful, failed,
                           success_rate, avg_processing_time_ms, avg_field_completeness, avg_consistency_rate, config
                    FROM evaluation_runs
                    WHERE id = %s
                    """,
                    (run_id,),
                )
                run_row = cursor.fetchone()
                if run_row is None:
                    return None

                cursor.execute(
                    """
                    SELECT filename, success, error_message,
                           processing_time_ms, fields_extracted, field_completeness,
                           product_count, has_vendor, has_date, has_total,
                           products_sum, extracted_total, total_difference, is_consistent,
                           result
                    FROM evaluation_results
                    WHERE run_id = %s
                    ORDER BY id
                    """,
                    (run_id,),
                )
                result_rows = cursor.fetchall()

            results: list[EvaluationResult] = []
            for r in result_rows:
                metrics = None
                if r[1]:  # success
                    try:
                        metrics = EvaluationMetrics(
                            processing_time_ms=r[3] or 0,
                            fields_extracted=r[4] or 0,
                            field_completeness=float(r[5] or 0),
                            product_count=r[6] or 0,
                            has_vendor=bool(r[7]),
                            has_date=bool(r[8]),
                            has_total=bool(r[9]),
                            products_sum=float(r[10] or 0),
                            extracted_total=float(r[11] or 0),
                            total_difference=float(r[12] or 0),
                            is_consistent=bool(r[13]),
                        )
                    except Exception:
                        pass
                transaction = None
                if r[14]:
                    try:
                        transaction = TransactionModel(**r[14])
                    except Exception:
                        pass
                results.append(EvaluationResult(
                    filename=r[0],
                    success=r[1],
                    error_message=r[2],
                    metrics=metrics,
                    transaction=transaction,
                ))

            return EvaluationRunDetail(
                id=run_row[0],
                run_timestamp=run_row[1],
                model_used=run_row[2],
                total_files=run_row[3],
                successful=run_row[4],
                failed=run_row[5],
                success_rate=float(run_row[6]) if run_row[6] is not None else None,
                avg_processing_time_ms=float(run_row[7]) if run_row[7] is not None else None,
                avg_field_completeness=float(run_row[8]) if run_row[8] is not None else None,
                avg_consistency_rate=float(run_row[9]) if run_row[9] is not None else None,
                config=run_row[10],
                results=results,
            )
        except Exception as e:
            print("Failed to fetch evaluation run with results:", e)
            return None
