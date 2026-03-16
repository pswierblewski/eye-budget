from dotenv import load_dotenv

load_dotenv()

from ..celery_app import celery_app
from ..app import App


@celery_app.task(name="tasks.advance_goal_progress")
def advance_goal_progress_task():
    """Monthly Celery beat task: advance accumulated progress for all active goals."""
    my_app = App()
    try:
        my_app.budget_goals_repository.advance_monthly_progress_for_all_active_goals()
        print("advance_goal_progress_task: completed successfully")
    except Exception as exc:
        print(f"advance_goal_progress_task error: {exc}")
        raise
    finally:
        my_app.dispose()
