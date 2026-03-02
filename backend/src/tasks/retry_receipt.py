import os
from dotenv import load_dotenv

load_dotenv()

from ..celery_app import celery_app
from ..app import App
from ..services.pusher_service import PusherService


@celery_app.task(bind=True, name="tasks.retry_receipt")
def retry_receipt_task(self, scan_id: int):
    """Celery task: re-run the full OCR pipeline for a single receipt scan."""
    task_id = self.request.id
    pusher = PusherService()
    my_app = App()
    try:
        success = my_app.retry_receipt(scan_id)
        if success:
            pusher.trigger("receipts", "receipt.done", {"task_id": task_id, "scan_id": scan_id})
        else:
            pusher.trigger(
                "receipts",
                "receipt.error",
                {"task_id": task_id, "scan_id": scan_id, "error": "Scan not found or file missing"},
            )
    except Exception as exc:
        pusher.trigger(
            "receipts",
            "receipt.error",
            {"task_id": task_id, "scan_id": scan_id, "error": str(exc)},
        )
        raise
    finally:
        my_app.dispose()
