from src.app import App
from src.data import EvaluationRunSummary, GroundTruthResponse, TransactionModel
from fastapi import FastAPI, File, UploadFile, HTTPException

app = FastAPI()


@app.post("/receipts/process")
def process_receipts():
    my_app = App()
    my_app.run()
    my_app.dispose()


@app.post("/receipts/sync-clients")
def sync_clients() -> dict:
    """
    Push all already-processed receipts to every configured budget client
    that hasn't received them yet.

    Useful when a new client is added and you want to backfill its database
    with all receipts that were processed before the client was configured.

    Returns a summary: {client_name: {synced, skipped, failed}}.
    """
    my_app = App()
    try:
        return my_app.sync_clients()
    finally:
        my_app.dispose()


@app.post("/receipts/evaluate", response_model=EvaluationRunSummary)
def evaluate_receipts() -> EvaluationRunSummary:
    """
    Run evaluation mode: process ground truth entries and compare OCR results
    against stored ground truth data.
    """
    my_app = App()
    result = my_app.run(evaluate=True)
    my_app.dispose()
    return result


# Ground Truth Management Endpoints

@app.post("/ground-truth", response_model=GroundTruthResponse)
async def create_ground_truth(file: UploadFile = File(...)) -> GroundTruthResponse:
    """
    Upload receipt image, run OCR, and store as ground truth draft.
    
    The OCR result can be corrected later using the PUT endpoint.
    Returns the created entry with ID for future reference.
    """
    my_app = App()
    try:
        # Read file content
        file_data = await file.read()
        filename = file.filename or "unknown.png"
        
        # Create ground truth entry
        result = my_app.create_ground_truth(filename, file_data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        my_app.dispose()


@app.put("/ground-truth/{entry_id}", response_model=GroundTruthResponse)
def update_ground_truth(entry_id: int, data: TransactionModel) -> GroundTruthResponse:
    """
    Update ground truth with corrected transaction data.
    
    Use this to fix any OCR errors in the ground truth entry.
    """
    my_app = App()
    try:
        result = my_app.update_ground_truth(entry_id, data)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Ground truth entry {entry_id} not found")
        return result
    finally:
        my_app.dispose()


@app.get("/ground-truth/{entry_id}", response_model=GroundTruthResponse)
def get_ground_truth(entry_id: int) -> GroundTruthResponse:
    """
    Get a single ground truth entry by ID.
    """
    my_app = App()
    try:
        result = my_app.get_ground_truth(entry_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Ground truth entry {entry_id} not found")
        return result
    finally:
        my_app.dispose()


@app.get("/ground-truth", response_model=list[GroundTruthResponse])
def list_ground_truth() -> list[GroundTruthResponse]:
    """
    List all ground truth entries.
    """
    my_app = App()
    try:
        return my_app.list_ground_truth()
    finally:
        my_app.dispose()
