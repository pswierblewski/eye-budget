import os
from dotenv import load_dotenv

load_dotenv()

from ..celery_app import celery_app
from ..app import App
from ..services.pusher_service import PusherService


@celery_app.task(bind=True, name="tasks.process_receipts")
def process_receipts_task(self):
    """Celery task: run the production receipt processing pipeline."""
    task_id = self.request.id
    pusher = PusherService()
    my_app = App()

    def on_progress(index: int, total: int, filename: str, status: str):
        pusher.trigger(
            "receipts",
            "receipt.progress",
            {
                "task_id": task_id,
                "index": index,
                "total": total,
                "filename": os.path.basename(filename),
                "status": status,
            },
        )

    try:
        my_app.run(evaluate=False, on_progress=on_progress)
        pusher.trigger(
            "receipts",
            "receipt.done",
            {"task_id": task_id},
        )
    except Exception as exc:
        pusher.trigger(
            "receipts",
            "receipt.error",
            {"task_id": task_id, "error": str(exc)},
        )
        raise
    finally:
        my_app.dispose()
