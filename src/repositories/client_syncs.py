from src.db_contexts.eye_budget import EyeBudgetDbContext


class ClientSyncsRepository:
    def __init__(self, db_context: EyeBudgetDbContext):
        self.conn = db_context.conn

    def is_synced(self, receipt_scan_id: int, client_name: str) -> bool:
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM client_syncs WHERE receipt_scan_id = %s AND client_name = %s AND status = 'synced'",
                (receipt_scan_id, client_name),
            )
            return cursor.fetchone() is not None

    def record_success(self, receipt_scan_id: int, client_name: str, external_id: str) -> None:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO client_syncs (receipt_scan_id, client_name, external_id, status, synced_at)
                VALUES (%s, %s, %s, 'synced', NOW())
                ON CONFLICT (receipt_scan_id, client_name)
                DO UPDATE SET external_id = EXCLUDED.external_id,
                              status = 'synced',
                              synced_at = NOW(),
                              error_message = NULL
                """,
                (receipt_scan_id, client_name, external_id),
            )
            self.conn.commit()

    def record_failure(self, receipt_scan_id: int, client_name: str, error: Exception) -> None:
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO client_syncs (receipt_scan_id, client_name, status, error_message, synced_at)
                VALUES (%s, %s, 'failed', %s, NOW())
                ON CONFLICT (receipt_scan_id, client_name)
                DO UPDATE SET status = 'failed',
                              error_message = EXCLUDED.error_message,
                              synced_at = NOW()
                """,
                (receipt_scan_id, client_name, str(error)),
            )
            self.conn.commit()

    def dispose(self) -> None:
        print("ClientSyncsRepository disposed.")
