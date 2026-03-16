from dotenv import load_dotenv

load_dotenv()

from ..celery_app import celery_app
from ..app import App
from ..services.pusher_service import PusherService


@celery_app.task(bind=True, name="tasks.run_budget_simulation")
def run_budget_simulation_task(self, simulation_id: int):
    """Run budget simulation projection and generate AI narrative."""
    pusher = PusherService()
    my_app = App()
    try:
        my_app.budget_simulations_repository.update_simulation_status(
            simulation_id, "processing"
        )
        sim_row = my_app.budget_simulations_repository.get_simulation(simulation_id)
        if sim_row is None:
            raise ValueError(f"Simulation {simulation_id} not found")

        result = my_app.budget_simulation_service.run_projection(sim_row)
        my_app.budget_simulations_repository.update_simulation_status(
            simulation_id, "done", result_json=result.model_dump()
        )
        pusher.trigger(
            "budget-channel",
            "budget.simulation.done",
            {"simulation_id": simulation_id, "status": "done"},
        )
    except Exception as exc:
        error_msg = str(exc)
        my_app.budget_simulations_repository.update_simulation_status(
            simulation_id, "failed", error=error_msg
        )
        pusher.trigger(
            "budget-channel",
            "budget.simulation.failed",
            {"simulation_id": simulation_id, "error": error_msg},
        )
        raise
    finally:
        my_app.dispose()
