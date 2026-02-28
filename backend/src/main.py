from dotenv import load_dotenv
load_dotenv()

from src.app import App
from src.celery_app import celery_app
from src.tasks.process_receipts import process_receipts_task
from src.tasks.run_evaluation import run_evaluation_task
from src.tasks.categorize_bank_transactions import categorize_bank_transactions_task
from src.data import (
    EvaluationRunSummary,
    GroundTruthResponse,
    TransactionModel,
    ReceiptScanListItem,
    ReceiptScanDetail,
    CategoryItem,
    CreateCategoryRequest,
    ConfirmReceiptRequest,
    EvaluationRunListItem,
    EvaluationRunDetail,
    VendorItem,
    NormalizedProductItem,
    BankTransactionListItem,
    BankTransactionDetail,
    BankImportResult,
    ConfirmBankTransactionRequest,
    ReceiptCandidateItem,
    BankTxCandidateItem,
    LinkReceiptRequest,
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

@app.get("/categories/groups", response_model=list[str])
def list_category_groups() -> list[str]:
    """Return all distinct category group names."""
    my_app = App()
    try:
        return my_app.get_all_category_groups()
    finally:
        my_app.dispose()


@app.get("/categories", response_model=list[CategoryItem])
def list_categories() -> list[CategoryItem]:
    """Return all expense categories with parent and group context."""
    my_app = App()
    try:
        return my_app.get_all_expense_categories()
    finally:
        my_app.dispose()


@app.post("/categories", response_model=CategoryItem, status_code=201)
def create_category(request: CreateCategoryRequest) -> CategoryItem:
    """Create a new expense category."""
    my_app = App()
    try:
        result = my_app.create_category(request.name, request.group_name, request.parent_id)
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to create category")
        return result
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


# ------------------------------------------------------------------
# Bank Transactions (CSV import)
# ------------------------------------------------------------------

@app.post("/bank-transactions/import", response_model=BankImportResult, status_code=201)
async def import_bank_transactions(file: UploadFile = File(...)) -> BankImportResult:
    """Import a Pekao SA CSV export. New transactions are deduplicated by reference number.
    LLM categorization runs in the background via Celery — poll /tasks/{task_id} for status."""
    my_app = App()
    try:
        data = await file.read()
        result, new_ids = my_app.import_bank_csv(data)
        if new_ids:
            task = categorize_bank_transactions_task.delay(new_ids)
            result.task_id = task.id
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        my_app.dispose()


@app.get("/bank-transactions", response_model=list[BankTransactionListItem])
def list_bank_transactions(status: str | None = None) -> list[BankTransactionListItem]:
    """List bank transactions, optionally filtered by status (to_confirm | done)."""
    my_app = App()
    try:
        return my_app.get_all_bank_transactions(status)
    finally:
        my_app.dispose()


@app.get("/bank-transactions/{tx_id}", response_model=BankTransactionDetail)
def get_bank_transaction(tx_id: int) -> BankTransactionDetail:
    """Get full detail for a single bank transaction including LLM category candidates."""
    my_app = App()
    try:
        result = my_app.get_bank_transaction_by_id(tx_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Bank transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()


@app.post("/bank-transactions/{tx_id}/confirm", response_model=BankTransactionDetail)
def confirm_bank_transaction(
    tx_id: int, request: ConfirmBankTransactionRequest
) -> BankTransactionDetail:
    """Confirm a category for a bank transaction and mark it as done."""
    my_app = App()
    try:
        result = my_app.confirm_bank_transaction(tx_id, request)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Bank transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()


@app.post("/bank-transactions/{tx_id}/reopen", response_model=BankTransactionDetail)
def reopen_bank_transaction(tx_id: int) -> BankTransactionDetail:
    """Reset a confirmed bank transaction back to to_confirm for re-categorization."""
    my_app = App()
    try:
        result = my_app.reopen_bank_transaction(tx_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Bank transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()


# ------------------------------------------------------------------
# Bank ↔ Receipt linking
# ------------------------------------------------------------------

@app.get("/bank-transactions/{tx_id}/receipt-candidates", response_model=list[ReceiptCandidateItem])
def get_receipt_candidates(tx_id: int) -> list[ReceiptCandidateItem]:
    """Return receipt_transaction candidates that could be linked to this bank transaction."""
    my_app = App()
    try:
        return my_app.get_receipt_candidates_for_bank_tx(tx_id)
    finally:
        my_app.dispose()


@app.get("/receipts/{scan_id}/bank-transaction-candidates", response_model=list[BankTxCandidateItem])
def get_bank_tx_candidates(scan_id: int) -> list[BankTxCandidateItem]:
    """Return bank_transaction candidates that could be linked to this receipt scan."""
    my_app = App()
    try:
        return my_app.get_bank_tx_candidates_for_receipt(scan_id)
    finally:
        my_app.dispose()


@app.post("/bank-transactions/{tx_id}/link", response_model=BankTransactionDetail)
def link_bank_to_receipt(tx_id: int, request: LinkReceiptRequest) -> BankTransactionDetail:
    """Link a bank transaction to a receipt transaction."""
    my_app = App()
    try:
        result = my_app.link_bank_to_receipt(tx_id, request)
        if result is None:
            raise HTTPException(
                status_code=409,
                detail="Link already exists or the receipt_transaction_id is already linked to another bank transaction.",
            )
        return result
    finally:
        my_app.dispose()


@app.delete("/bank-transactions/{tx_id}/link", response_model=BankTransactionDetail)
def unlink_bank_transaction(tx_id: int) -> BankTransactionDetail:
    """Remove the link between a bank transaction and a receipt."""
    my_app = App()
    try:
        result = my_app.unlink_bank_transaction(tx_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Bank transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()
