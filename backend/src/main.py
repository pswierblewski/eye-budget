from dotenv import load_dotenv
load_dotenv()

from src.app import App
from src.celery_app import celery_app
from src.tasks.process_receipts import process_receipts_task
from src.tasks.run_evaluation import run_evaluation_task
from src.data import (
    EvaluationRunSummary,
    GroundTruthResponse,
    TransactionModel,
    ReceiptScanListItem,
    ReceiptScanDetail,
    CategoryItem,
    ConfirmReceiptRequest,
    EvaluationRunListItem,
    EvaluationRunDetail,
    VendorItem,
    NormalizedProductItem,
)
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

app = FastAPI()


class TaskResponse(BaseModel):
    task_id: str


@app.post("/receipts/process", response_model=TaskResponse, status_code=202)
def process_receipts():
    """Dispatch receipt processing to a background Celery worker. Returns immediately."""
    task = process_receipts_task.delay()
    return TaskResponse(task_id=task.id)


@app.post("/receipts/evaluate", response_model=TaskResponse, status_code=202)
def evaluate_receipts():
    """Dispatch evaluation run to a background Celery worker. Returns immediately."""
    task = run_evaluation_task.delay()
    return TaskResponse(task_id=task.id)


@app.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    """Poll the status of a background task by its Celery task ID."""
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.successful() else None,
        "error": str(result.result) if result.failed() else None,
    }


# ------------------------------------------------------------------
# Receipts read + confirm endpoints
# ------------------------------------------------------------------

@app.get("/receipts", response_model=list[ReceiptScanListItem])
def list_receipts() -> list[ReceiptScanListItem]:
    """List all receipt scans, newest first."""
    my_app = App()
    try:
        return my_app.get_all_receipts()
    finally:
        my_app.dispose()


@app.get("/receipts/{scan_id}", response_model=ReceiptScanDetail)
def get_receipt(scan_id: int) -> ReceiptScanDetail:
    """Get full scan detail including confirmed transaction if present."""
    my_app = App()
    try:
        result = my_app.get_receipt_by_id(scan_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Receipt scan {scan_id} not found")
        return result
    finally:
        my_app.dispose()


@app.get("/receipts/{scan_id}/image")
def get_receipt_image(scan_id: int) -> StreamingResponse:
    """Proxy the preprocessed receipt image stored in MinIO."""
    my_app = App()
    try:
        image_bytes = my_app.get_receipt_image_bytes(scan_id)
        if image_bytes is None:
            raise HTTPException(status_code=404, detail=f"Image for scan {scan_id} not found")
        return StreamingResponse(io.BytesIO(image_bytes), media_type="image/png")
    finally:
        my_app.dispose()


@app.post("/receipts/{scan_id}/confirm", response_model=ReceiptScanDetail)
def confirm_receipt(scan_id: int, request: ConfirmReceiptRequest) -> ReceiptScanDetail:
    """
    Confirm receipt categories.

    Receives a mapping of raw product names to category IDs, creates a
    receipt_transaction with items, and marks the scan as done.
    Optionally accepts overrides for vendor, date, total, and products to
    correct any OCR errors before the transaction is created.
    """
    my_app = App()
    try:
        result = my_app.confirm_receipt(scan_id, request)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Receipt scan {scan_id} not found or has no OCR result")
        return result
    finally:
        my_app.dispose()


@app.post("/receipts/{scan_id}/reopen", response_model=ReceiptScanDetail)
def reopen_receipt(scan_id: int) -> ReceiptScanDetail:
    """
    Reopen a confirmed receipt for editing.

    Deletes the existing transaction rows and resets the scan status back to
    to_confirm, allowing categories and OCR-sourced fields to be corrected
    before re-confirming.
    """
    my_app = App()
    try:
        result = my_app.reopen_receipt(scan_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Receipt scan {scan_id} not found")
        return result
    finally:
        my_app.dispose()


# ------------------------------------------------------------------
# Vendors
# ------------------------------------------------------------------

class CreateVendorRequest(BaseModel):
    name: str


@app.get("/vendors", response_model=list[VendorItem])
def list_vendors() -> list[VendorItem]:
    """Return all vendors ordered alphabetically."""
    my_app = App()
    try:
        return my_app.get_all_vendors()
    finally:
        my_app.dispose()


@app.post("/vendors", response_model=VendorItem, status_code=201)
def create_vendor(request: CreateVendorRequest) -> VendorItem:
    """Create a new vendor by normalized name."""
    my_app = App()
    try:
        result = my_app.create_vendor(request.name)
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to create vendor")
        return result
    finally:
        my_app.dispose()


# ------------------------------------------------------------------
# Products
# ------------------------------------------------------------------

class CreateProductRequest(BaseModel):
    name: str


@app.get("/products", response_model=list[NormalizedProductItem])
def list_products() -> list[NormalizedProductItem]:
    """Return all normalized products ordered alphabetically."""
    my_app = App()
    try:
        return my_app.get_all_products()
    finally:
        my_app.dispose()


@app.post("/products", response_model=NormalizedProductItem, status_code=201)
def create_product(request: CreateProductRequest) -> NormalizedProductItem:
    """Create a new normalized product."""
    my_app = App()
    try:
        result = my_app.create_product(request.name)
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to create product")
        return result
    finally:
        my_app.dispose()



# ------------------------------------------------------------------
# Categories
# ------------------------------------------------------------------

@app.get("/categories", response_model=list[CategoryItem])
def list_categories() -> list[CategoryItem]:
    """Return all expense categories with parent and group context."""
    my_app = App()
    try:
        return my_app.get_all_expense_categories()
    finally:
        my_app.dispose()


# ------------------------------------------------------------------
# Evaluations
# ------------------------------------------------------------------

@app.get("/evaluations", response_model=list[EvaluationRunListItem])
def list_evaluations() -> list[EvaluationRunListItem]:
    """List all evaluation runs, newest first."""
    my_app = App()
    try:
        return my_app.get_all_evaluation_runs()
    finally:
        my_app.dispose()


@app.get("/evaluations/{run_id}", response_model=EvaluationRunDetail)
def get_evaluation(run_id: int) -> EvaluationRunDetail:
    """Get a single evaluation run with all per-file results."""
    my_app = App()
    try:
        result = my_app.get_evaluation_run(run_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Evaluation run {run_id} not found")
        return result
    finally:
        my_app.dispose()


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


@app.get("/ground-truth/{entry_id}/image")
def get_ground_truth_image(entry_id: int) -> StreamingResponse:
    """Proxy the receipt image for a ground truth entry stored in MinIO."""
    my_app = App()
    try:
        image_bytes = my_app.get_ground_truth_image_bytes(entry_id)
        if image_bytes is None:
            raise HTTPException(status_code=404, detail=f"Image for ground truth entry {entry_id} not found")
        return StreamingResponse(io.BytesIO(image_bytes), media_type="image/png")
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
