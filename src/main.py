from src.app import App
from src.data import EvaluationRunSummary
from fastapi import FastAPI

app = FastAPI()


@app.post("/receipts/process")
def process_receipts():
    my_app = App()
    my_app.run()
    my_app.dispose()


@app.post("/receipts/evaluate", response_model=EvaluationRunSummary)
def evaluate_receipts() -> EvaluationRunSummary:
    """
    Run evaluation mode: process receipts from evaluate/ directory
    and return metrics without affecting production database.
    """
    my_app = App()
    result = my_app.run(evaluate=True)
    my_app.dispose()
    return result
