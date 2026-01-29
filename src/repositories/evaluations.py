from abc import ABC
from psycopg2 import extras

from ..data import EvaluationResult, EvaluationMetrics, EvaluationRunSummary


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
