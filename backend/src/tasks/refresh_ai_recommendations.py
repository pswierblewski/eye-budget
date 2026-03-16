import datetime
from dotenv import load_dotenv

load_dotenv()

from ..celery_app import celery_app
from ..app import App
from ..services.pusher_service import PusherService


@celery_app.task(name="tasks.refresh_ai_recommendations")
def refresh_ai_recommendations_task():
    """Generate fresh AI budget recommendations and push Pusher event."""
    pusher = PusherService()
    my_app = App()
    try:
        result = my_app.budget_simulation_service.generate_ai_recommendations()
        pusher.trigger(
            "budget-channel",
            "budget.recommendations.done",
            {"generated_at": datetime.datetime.now().isoformat()},
        )
        return {"has_sufficient_data": result.has_sufficient_data}
    except Exception as exc:
        print(f"refresh_ai_recommendations_task error: {exc}")
        raise
    finally:
        my_app.dispose()
