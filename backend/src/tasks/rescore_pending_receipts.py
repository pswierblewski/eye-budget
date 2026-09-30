from dotenv import load_dotenv

load_dotenv()

from ..celery_app import celery_app
from ..app import App
from ..services.pusher_service import PusherService


@celery_app.task(bind=True, name="tasks.rescore_pending_receipts")
def rescore_pending_receipts_task(self, dry_run: bool = True):
    """Celery task: re-score to_confirm receipts with history-based categorization."""
    task_id = self.request.id
    pusher = PusherService()
    my_app = App()

    def on_progress(index: int, total: int):
        pusher.trigger(
            "receipts",
            "receipt.rescore_progress",
            {"task_id": task_id, "index": index, "total": total},
        )

    try:
        report = my_app.rescore_pending_receipts(dry_run=dry_run, on_progress=on_progress).model_dump()
        pusher.trigger("receipts", "receipt.rescore_done", {"task_id": task_id, "report": report})
        return report
    except Exception as exc:
        pusher.trigger("receipts", "receipt.rescore_error", {"task_id": task_id, "error": str(exc)})
        raise
    finally:
        my_app.dispose()
