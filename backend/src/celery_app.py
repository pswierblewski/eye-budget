import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
# Use DB 1 for results to keep broker and result backend separate
REDIS_BACKEND_URL = os.environ.get("REDIS_BACKEND_URL", REDIS_URL.rstrip("0") + "1")

celery_app = Celery(
    "eye_budget",
    broker=REDIS_URL,
    backend=REDIS_BACKEND_URL,
    include=[
        "src.tasks.process_receipts",
        "src.tasks.run_evaluation",
        "src.tasks.categorize_bank_transactions",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,  # keep results for 1 hour
)
