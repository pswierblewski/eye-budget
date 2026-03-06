from dotenv import load_dotenv
load_dotenv()

from typing import Optional

from src.app import App
from src.celery_app import celery_app
from src.tasks.process_receipts import process_receipts_task
from src.tasks.run_evaluation import run_evaluation_task
from src.tasks.retry_receipt import retry_receipt_task
from src.tasks.categorize_bank_transactions import categorize_bank_transactions_task
from src.data import (
    EvaluationRunSummary,
    GroundTruthResponse,
    TransactionModel,
    ReceiptScanListItem,
    ReceiptScanDetail,
    ReceiptTransactionItem,
    CategoryItem,
    CreateCategoryRequest,
    ConfirmReceiptRequest,
    UpdateTransactionItemRequest,
    EvaluationRunListItem,
    EvaluationRunDetail,
    VendorItem,
    NormalizedProductItem,
    BankTransactionListItem,
    BankTransactionDetail,
    BankImportResult,
    RecategorizeBankTransactionsResult,
    UpdateBankTransactionCategoryRequest,
    ReceiptCandidateItem,
    BankTxCandidateItem,
    LinkReceiptRequest,
    CashTransactionListItem,
    CashTransactionDetail,
    CashTransactionCreate,
    CashTransactionUpdate,
    UpdateCashTransactionCategoryRequest,
    LinkCashReceiptRequest,
    CashTxCandidateItem,
    PaginatedResponse,
    UpdateTagsRequest,
    UnifiedTransaction,
    AnalyticsSummary,
    RunEvaluationRequest,
    PromptAnalyticsSummary,
)
from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io
import threading
from cachetools import TTLCache

app = FastAPI()

# Cache preprocessed image bytes in memory. Entries expire after 1 h to match
# the browser Cache-Control header and the presigned-URL TTL.
_image_cache: TTLCache = TTLCache(maxsize=256, ttl=3600)
_image_cache_lock = threading.Lock()


class TaskResponse(BaseModel):
    task_id: str


@app.post("/receipts/process", response_model=TaskResponse, status_code=202)
def process_receipts():
    """Dispatch receipt processing to a background Celery worker. Returns immediately."""
    task = process_receipts_task.delay()
    return TaskResponse(task_id=task.id)


@app.post("/receipts/evaluate", response_model=TaskResponse, status_code=202)
def evaluate_receipts(request: RunEvaluationRequest = RunEvaluationRequest()):
    """Dispatch evaluation run to a background Celery worker. Returns immediately."""
    task = run_evaluation_task.delay(entry_ids=request.entry_ids)
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

@app.get("/receipts/counts")
def get_receipt_counts() -> dict[str, int]:
    """Return count of receipt scans per status."""
    my_app = App()
    try:
        return my_app.get_receipt_status_counts()
    finally:
        my_app.dispose()


@app.get("/receipts", response_model=PaginatedResponse[ReceiptScanListItem])
def list_receipts(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "id",
    sort_dir: str = "desc",
    search: str | None = None,
    vendor: str | None = None,
    product: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    total_min: float | None = None,
    total_max: float | None = None,
    tag: str | None = None,
) -> PaginatedResponse[ReceiptScanListItem]:
    """List receipt scans, paginated, with optional filters."""
    my_app = App()
    try:
        items, total = my_app.get_all_receipts(
            status=status, limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir,
            search=search, vendor=vendor, product=product,
            date_from=date_from, date_to=date_to,
            total_min=total_min, total_max=total_max,
            tag=tag,
        )
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
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
    """Proxy the preprocessed receipt image stored in MinIO (with in-process cache)."""
    with _image_cache_lock:
        if scan_id in _image_cache:
            return StreamingResponse(io.BytesIO(_image_cache[scan_id]), media_type="image/jpeg")
    my_app = App()
    try:
        image_bytes = my_app.get_receipt_image_bytes(scan_id)
        if image_bytes is None:
            raise HTTPException(status_code=404, detail=f"Image for scan {scan_id} not found")
        with _image_cache_lock:
            _image_cache[scan_id] = image_bytes
        return StreamingResponse(io.BytesIO(image_bytes), media_type="image/jpeg")
    finally:
        my_app.dispose()


@app.get("/receipts/{scan_id}/image-url")
def get_receipt_image_url(scan_id: int, expires: int = 3600):
    """Return a presigned MinIO URL so the browser can fetch the image directly."""
    my_app = App()
    try:
        url = my_app.get_receipt_image_url(scan_id, expires_sec=expires)
        if url is None:
            raise HTTPException(status_code=404, detail=f"Image for scan {scan_id} not found")
        return {"url": url, "expires_in": expires}
    finally:
        my_app.dispose()


@app.post("/receipts/{scan_id}/reupload-image")
def reupload_receipt_image(scan_id: int):
    """
    Re-preprocess the source image from the input directory and re-upload it to
    MinIO.  Use this when the receipt image is missing (e.g. MinIO was reset or
    preprocessing failed mid-way on first run).
    """
    my_app = App()
    try:
        ok = my_app.reupload_receipt_image(scan_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Could not reupload image for scan {scan_id} — source file may be missing")
        with _image_cache_lock:
            _image_cache.pop(scan_id, None)
        return {"ok": True}
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


@app.patch("/receipts/items/{item_id}", response_model=ReceiptTransactionItem)
def update_transaction_item(
    item_id: int, request: UpdateTransactionItemRequest
) -> ReceiptTransactionItem:
    """
    Update individual fields on a confirmed receipt transaction item.

    Accepts any combination of: category_id, product_id, quantity, unit_price, price.
    Only supplied (non-null) fields are updated.
    """
    my_app = App()
    try:
        result = my_app.update_transaction_item(item_id, request)
        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Transaction item {item_id} not found or no fields to update",
            )
        return result
    finally:
        my_app.dispose()


@app.delete("/receipts/items/{item_id}", status_code=200)
def delete_transaction_item(item_id: int):
    """
    Delete a single confirmed receipt transaction item.
    """
    my_app = App()
    try:
        ok = my_app.delete_transaction_item(item_id)
        if not ok:
            raise HTTPException(
                status_code=404,
                detail=f"Transaction item {item_id} not found",
            )
        return {"ok": True}
    finally:
        my_app.dispose()


@app.delete("/receipts/{scan_id}", status_code=200)
def delete_receipt(scan_id: int):
    """
    Permanently delete a receipt scan together with its confirmed transaction,
    line items, bank links and MinIO image.
    """
    my_app = App()
    try:
        ok = my_app.delete_receipt(scan_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Receipt scan {scan_id} not found")
        return {"ok": True}
    finally:
        my_app.dispose()


@app.post("/receipts/{scan_id}/retry", response_model=TaskResponse, status_code=202)
def retry_receipt(scan_id: int):
    """
    Re-run the full OCR pipeline for a single receipt scan.

    Resets the scan status to 'pending' and dispatches a background Celery task
    that re-runs preprocessing, OCR, vendor/product normalisation and category
    candidate assignment for the given scan.  Available for scans in status
    new / processing / processed / failed.
    """
    task = retry_receipt_task.delay(scan_id)
    return TaskResponse(task_id=task.id)


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


@app.post("/categories", response_model=CategoryItem, status_code=201)
def create_category(request: CreateCategoryRequest) -> CategoryItem:
    """Create a new expense category."""
    my_app = App()
    try:
        result = my_app.create_category(request.name, request.parent_id)
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to create category")
        return result
    finally:
        my_app.dispose()


# ------------------------------------------------------------------
# Evaluations
# ------------------------------------------------------------------

@app.get("/evaluations", response_model=PaginatedResponse[EvaluationRunListItem])
def list_evaluations(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "id",
    sort_dir: str = "desc",
) -> PaginatedResponse[EvaluationRunListItem]:
    """List evaluation runs, paginated, newest first."""
    my_app = App()
    try:
        items, total = my_app.get_all_evaluation_runs(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir
        )
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
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


@app.get("/ground-truth", response_model=PaginatedResponse[GroundTruthResponse])
def list_ground_truth(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "id",
    sort_dir: str = "desc",
) -> PaginatedResponse[GroundTruthResponse]:
    """
    List ground truth entries, paginated.
    """
    my_app = App()
    try:
        items, total = my_app.list_ground_truth(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir
        )
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
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


@app.post("/bank-transactions/recategorize", response_model=RecategorizeBankTransactionsResult, status_code=202)
def recategorize_bank_transactions() -> RecategorizeBankTransactionsResult:
    """Queue LLM categorization for all bank transactions that have no candidates and no receipt link.

    Returns immediately with the Celery task_id and the number of transactions queued.
    If there is nothing to process, task_id is null and count is 0.
    """
    my_app = App()
    try:
        ids = my_app.get_bank_tx_ids_for_recategorization()
        if not ids:
            return RecategorizeBankTransactionsResult(task_id=None, count=0)
        task = categorize_bank_transactions_task.delay(ids)
        return RecategorizeBankTransactionsResult(task_id=task.id, count=len(ids))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        my_app.dispose()


@app.get("/bank-transactions", response_model=PaginatedResponse[BankTransactionListItem])
def list_bank_transactions(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "booking_date",
    sort_dir: str = "desc",
    tag: str | None = None,
) -> PaginatedResponse[BankTransactionListItem]:
    """List bank transactions, paginated."""
    my_app = App()
    try:
        items, total = my_app.get_all_bank_transactions(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir,
            tag=tag,
        )
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
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


@app.delete("/bank-transactions/{tx_id}", status_code=204)
def delete_bank_transaction(tx_id: int) -> None:
    """Delete a bank transaction."""
    my_app = App()
    try:
        ok = my_app.delete_bank_transaction(tx_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Bank transaction {tx_id} not found")
    finally:
        my_app.dispose()


@app.patch("/bank-transactions/{tx_id}/category", response_model=BankTransactionDetail)
def update_bank_transaction_category(
    tx_id: int, request: UpdateBankTransactionCategoryRequest
) -> BankTransactionDetail:
    """Update the category of a bank transaction."""
    my_app = App()
    try:
        result = my_app.update_bank_transaction_category(tx_id, request)
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


@app.get("/receipts/{scan_id}/cash-transaction-candidates", response_model=list[CashTxCandidateItem])
def get_cash_tx_candidates(scan_id: int) -> list[CashTxCandidateItem]:
    """Return cash_transaction candidates that could be linked to this receipt scan."""
    my_app = App()
    try:
        return my_app.get_cash_tx_candidates_for_receipt(scan_id)
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


# ------------------------------------------------------------------
# Tags
# ------------------------------------------------------------------

@app.get("/tags", response_model=list[str])
def get_all_tags() -> list[str]:
    """Return all distinct tags used across receipts and bank transactions."""
    my_app = App()
    try:
        return my_app.get_all_tags()
    finally:
        my_app.dispose()


@app.patch("/receipts/{scan_id}/tags", response_model=ReceiptScanDetail)
def update_receipt_tags(scan_id: int, request: UpdateTagsRequest) -> ReceiptScanDetail:
    """Replace the tags on a receipt scan and propagate to any linked bank transaction."""
    my_app = App()
    try:
        my_app.update_receipt_tags(scan_id, request.tags)
        result = my_app.get_receipt_by_id(scan_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Receipt scan {scan_id} not found")
        return result
    finally:
        my_app.dispose()


@app.patch("/bank-transactions/{tx_id}/tags", response_model=BankTransactionDetail)
def update_bank_transaction_tags(tx_id: int, request: UpdateTagsRequest) -> BankTransactionDetail:
    """Replace the tags on a bank transaction and propagate to any linked receipt."""
    my_app = App()
    try:
        my_app.update_bank_transaction_tags(tx_id, request.tags)
        result = my_app.get_bank_transaction_by_id(tx_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Bank transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()


# ------------------------------------------------------------------
# Cash Transactions
# ------------------------------------------------------------------

@app.get("/cash-transactions", response_model=PaginatedResponse[CashTransactionListItem])
def list_cash_transactions(
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "booking_date",
    sort_dir: str = "desc",
    tag: str | None = None,
) -> PaginatedResponse[CashTransactionListItem]:
    """List cash transactions, paginated."""
    my_app = App()
    try:
        items, total = my_app.get_all_cash_transactions(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir,
            tag=tag,
        )
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
    finally:
        my_app.dispose()


@app.post("/cash-transactions", response_model=CashTransactionDetail, status_code=201)
def create_cash_transaction(data: CashTransactionCreate) -> CashTransactionDetail:
    """Create a new manual cash transaction."""
    my_app = App()
    try:
        result = my_app.create_cash_transaction(data)
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to create cash transaction")
        return result
    finally:
        my_app.dispose()


@app.post("/cash-transactions/from-receipt/{scan_id}", response_model=CashTransactionDetail, status_code=201)
def create_cash_transaction_from_receipt(scan_id: int) -> CashTransactionDetail:
    """Auto-create a cash transaction from a confirmed receipt scan."""
    my_app = App()
    try:
        result = my_app.create_cash_transaction_from_receipt(scan_id)
        if result is None:
            raise HTTPException(
                status_code=400,
                detail=f"Receipt scan {scan_id} has no confirmed transaction or cash transaction already exists.",
            )
        return result
    finally:
        my_app.dispose()


@app.get("/cash-transactions/{tx_id}", response_model=CashTransactionDetail)
def get_cash_transaction(tx_id: int) -> CashTransactionDetail:
    """Get full detail for a single cash transaction."""
    my_app = App()
    try:
        result = my_app.get_cash_transaction_by_id(tx_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Cash transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()


@app.put("/cash-transactions/{tx_id}", response_model=CashTransactionDetail)
def update_cash_transaction(tx_id: int, data: CashTransactionUpdate) -> CashTransactionDetail:
    """Update fields of an existing cash transaction."""
    my_app = App()
    try:
        result = my_app.update_cash_transaction(tx_id, data)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Cash transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()


@app.delete("/cash-transactions/{tx_id}", status_code=204)
def delete_cash_transaction(tx_id: int) -> None:
    """Delete a cash transaction."""
    my_app = App()
    try:
        ok = my_app.delete_cash_transaction(tx_id)
        if not ok:
            raise HTTPException(status_code=404, detail=f"Cash transaction {tx_id} not found")
    finally:
        my_app.dispose()


@app.patch("/cash-transactions/{tx_id}/category", response_model=CashTransactionDetail)
def update_cash_transaction_category(
    tx_id: int, request: UpdateCashTransactionCategoryRequest
) -> CashTransactionDetail:
    """Update the category of a cash transaction."""
    my_app = App()
    try:
        result = my_app.update_cash_transaction_category(tx_id, request)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Cash transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()


@app.get("/cash-transactions/{tx_id}/receipt-candidates", response_model=list[ReceiptCandidateItem])
def get_cash_receipt_candidates(tx_id: int) -> list[ReceiptCandidateItem]:
    """Return receipt_transaction candidates that could be linked to this cash transaction."""
    my_app = App()
    try:
        return my_app.get_receipt_candidates_for_cash_tx(tx_id)
    finally:
        my_app.dispose()


@app.post("/cash-transactions/{tx_id}/link", response_model=CashTransactionDetail)
def link_cash_to_receipt(tx_id: int, request: LinkCashReceiptRequest) -> CashTransactionDetail:
    """Link a cash transaction to a receipt transaction."""
    my_app = App()
    try:
        result = my_app.link_cash_to_receipt(tx_id, request)
        if result is None:
            raise HTTPException(
                status_code=409,
                detail="Link already exists or the receipt_transaction_id is already linked to another cash transaction.",
            )
        return result
    finally:
        my_app.dispose()


@app.delete("/cash-transactions/{tx_id}/link", response_model=CashTransactionDetail)
def unlink_cash_transaction(tx_id: int) -> CashTransactionDetail:
    """Remove the link between a cash transaction and a receipt."""
    my_app = App()
    try:
        result = my_app.unlink_cash_transaction(tx_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Cash transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()


@app.patch("/cash-transactions/{tx_id}/tags", response_model=CashTransactionDetail)
def update_cash_transaction_tags(tx_id: int, request: UpdateTagsRequest) -> CashTransactionDetail:
    """Replace the tags on a cash transaction."""
    my_app = App()
    try:
        my_app.update_cash_transaction_tags(tx_id, request.tags)
        result = my_app.get_cash_transaction_by_id(tx_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Cash transaction {tx_id} not found")
        return result
    finally:
        my_app.dispose()


# ------------------------------------------------------------------
# Unified transactions
# ------------------------------------------------------------------

@app.get("/transactions", response_model=PaginatedResponse[UnifiedTransaction])
def list_unified_transactions(
    status: Optional[str] = Query(None),
    source_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    amount_min: Optional[float] = Query(None),
    amount_max: Optional[float] = Query(None),
    direction: Optional[str] = Query(None),
    sort_by: str = Query("date"),
    sort_dir: str = Query("desc"),
    limit: int = Query(50),
    offset: int = Query(0),
) -> PaginatedResponse[UnifiedTransaction]:
    """Return a paginated, filterable unified list of transactions."""
    my_app = App()
    try:
        items, total = my_app.get_unified_transactions(
            status=status,
            source_type=source_type,
            date_from=date_from,
            date_to=date_to,
            category_id=category_id,
            tag=tag,
            search=search,
            amount_min=amount_min,
            amount_max=amount_max,
            direction=direction,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
        return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
    finally:
        my_app.dispose()


@app.get("/transactions/analytics", response_model=AnalyticsSummary)
def get_transactions_analytics(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
) -> AnalyticsSummary:
    """Return aggregated analytics for the given date range."""
    my_app = App()
    try:
        return my_app.get_transactions_analytics(date_from=date_from, date_to=date_to)
    finally:
        my_app.dispose()


@app.get("/prompt-analytics", response_model=PromptAnalyticsSummary)
def get_prompt_analytics() -> PromptAnalyticsSummary:
    """Return aggregated AI prompt quality analytics."""
    my_app = App()
    try:
        return my_app.get_prompt_analytics()
    finally:
        my_app.dispose()
