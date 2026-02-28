import asyncio
from dotenv import load_dotenv

load_dotenv()

from ..celery_app import celery_app
from ..app import App
from ..services.pusher_service import PusherService


@celery_app.task(bind=True, name="tasks.run_evaluation")
def run_evaluation_task(self):
    """Celery task: run evaluation against all ground truth entries."""
    task_id = self.request.id
    pusher = PusherService()
    my_app = App()

    def on_progress(index: int, total: int, filename: str, success: bool):
        pusher.trigger(
            f"evaluation-{task_id}",
            "evaluation.progress",
            {
                "task_id": task_id,
                "index": index,
                "total": total,
                "filename": filename,
                "success": success,
            },
        )

    try:
        summary = asyncio.run(
            my_app.evaluation_service.run_evaluation_async(on_progress=on_progress)
        )
        pusher.trigger(
            f"evaluation-{task_id}",
            "evaluation.done",
            {
                "task_id": task_id,
                "summary": summary.model_dump() if summary else None,
            },
        )
        return summary.model_dump() if summary else None
    except Exception as exc:
        pusher.trigger(
            f"evaluation-{task_id}",
            "evaluation.error",
            {"task_id": task_id, "error": str(exc)},
        )
        raise
    finally:
        my_app.dispose()
