from abc import ABC
import asyncio
import os as _os_top

from src.services.preprocessing import PreprocessingService
from src.services.minio_storage import MinioStorageService
from src.services.evaluation import EvaluationService
from src.services.ground_truth import GroundTruthService
from src.services.vendors import VendorsService
from src.services.products import ProductsService
from src.services.categories import CategoriesService
from src.services.bank_categorization import BankCategorizationService
from src.services.bank_csv_parser import PekaoCsvParser
from .repositories.files import FilesRepository
from .repositories.vendors import VendorsRepository
from .repositories.products import ProductsRepository
from .services.ocr import OCRService
from .repositories.receipts_scans import ReceiptsScansRepository
from .repositories.evaluations import EvaluationsRepository
from .repositories.ground_truth import GroundTruthRepository
from .repositories.transactions import TransactionsRepository
from .repositories.categories import CategoriesRepository
from .repositories.bank_transactions import BankTransactionsRepository
from .repositories.bank_receipt_links import BankReceiptLinksRepository
from .repositories.cash_transactions import CashTransactionsRepository
from .repositories.cash_receipt_links import CashReceiptLinksRepository
from .repositories.unified_transactions import UnifiedTransactionsRepository
from .repositories.prompt_analytics import PromptAnalyticsRepository
from .data import (
    ReceiptsScanStatus,
    TransactionModel,
    EvaluationRunSummary,
    GroundTruthResponse,
    ReceiptScanListItem,
    ReceiptScanDetail,
    ReceiptTransaction,
    ReceiptTransactionItem,
    CategoryItem,
    ConfirmReceiptRequest,
    UpdateTransactionItemRequest,
    EvaluationRunListItem,
    EvaluationRunDetail,
    VendorItem,
    NormalizedProductItem,
    BankTransactionListItem,
    BankTransactionDetail,
    BankImportResult,
    UpdateBankTransactionCategoryRequest,
    ReceiptLinkInfo,
    BankLinkInfo,
    ReceiptCandidateItem,
    BankTxCandidateItem,
    LinkReceiptRequest,
    CashTransactionListItem,
    CashTransactionDetail,
    CashTransactionCreate,
    CashTransactionUpdate,
    UpdateCashTransactionCategoryRequest,
    LinkCashReceiptRequest,
    CashReceiptLinkInfo,
    CashLinkInfo,
    CashTxCandidateItem,
    UnifiedTransaction,
    AnalyticsSummary,
    PromptAnalyticsSummary,
)
from .db_contexts.eye_budget import EyeBudgetDbContext


class App(ABC):
    def __init__(self):
        # Database contexts
        self.eye_budget_db_context = EyeBudgetDbContext()

        # Repositories
        self.files_repository = FilesRepository()
        self.receipts_scans_repository = ReceiptsScansRepository(self.eye_budget_db_context)
        self.evaluations_repository = EvaluationsRepository(self.eye_budget_db_context)
        self.ground_truth_repository = GroundTruthRepository(self.eye_budget_db_context)
        self.vendors_repository = VendorsRepository(self.eye_budget_db_context)
        self.products_repository = ProductsRepository(self.eye_budget_db_context)
        self.transactions_repository = TransactionsRepository(self.eye_budget_db_context)
        self.categories_repository = CategoriesRepository(self.eye_budget_db_context)

        self.bank_transactions_repository = BankTransactionsRepository(self.eye_budget_db_context)
        self.bank_receipt_links_repository = BankReceiptLinksRepository(self.eye_budget_db_context)
        self.cash_transactions_repository = CashTransactionsRepository(self.eye_budget_db_context)
        self.cash_receipt_links_repository = CashReceiptLinksRepository(self.eye_budget_db_context)
        self.unified_transactions_repository = UnifiedTransactionsRepository(self.eye_budget_db_context)
        self.prompt_analytics_repository = PromptAnalyticsRepository(self.eye_budget_db_context)

        # Core services
        self.ocr_service = OCRService()
        self.preprocessing_service = PreprocessingService()
        self.minio_service = MinioStorageService()
        self.vendors_service = VendorsService()
        self.products_service = ProductsService()
        self.categories_service = CategoriesService(self.eye_budget_db_context)
        self.categories_service.build()
        self.bank_categorization_service = BankCategorizationService(self.eye_budget_db_context)
        self.bank_categorization_service.build()
        self.bank_csv_parser = PekaoCsvParser()

        # High-level services
        self.evaluation_service = EvaluationService(
            evaluations_repository=self.evaluations_repository,
            ground_truth_repository=self.ground_truth_repository,
            minio_service=self.minio_service,
            preprocessing_service=self.preprocessing_service,
            ocr_service=self.ocr_service
        )
        self.ground_truth_service = GroundTruthService(
            ground_truth_repository=self.ground_truth_repository,
            minio_service=self.minio_service,
            preprocessing_service=self.preprocessing_service,
            ocr_service=self.ocr_service
        )

    def get_all_vendors(self) -> list[VendorItem]:
        """Return all vendors ordered alphabetically."""
        return self.vendors_repository.get_all_vendors()

    def create_vendor(self, name: str) -> VendorItem | None:
        """Create a new vendor and return it."""
        vendor_id = self.vendors_repository.insert_vendor(name)
        if vendor_id is None:
            return None
        return VendorItem(id=vendor_id, name=name)

    def get_all_products(self) -> list[NormalizedProductItem]:
        """Return all normalized products ordered alphabetically."""
        return self.products_repository.get_all_products()

    def create_product(self, name: str) -> NormalizedProductItem | None:
        """Create a new normalized product and return it."""
        product_id = self.products_repository.insert_product(name)
        if product_id is None:
            return None
        return NormalizedProductItem(id=product_id, name=name)

    def run(self, evaluate: bool = False, on_progress=None) -> EvaluationRunSummary | None:
        """
        Run the receipt processing pipeline.

        Args:
            evaluate: If True, run evaluation against ground truth data.
                     Returns EvaluationRunSummary.
            on_progress: Optional callable(index, total, filename, status) called
                         after each file is processed.

        Returns:
            EvaluationRunSummary if evaluate=True, None otherwise.
        """
        if evaluate:
            return self.evaluation_service.run_evaluation(on_progress=on_progress)
        else:
            self._run_production(on_progress=on_progress)
            return None

    def _run_production(self, on_progress=None):
        """Run the standard production processing pipeline."""
        all_files = self.files_repository.list_input_files()
        if not all_files:
            print("No files to process.")
            return
        # Filter to only new files: attempt add, keep those successfully added
        new_files = []
        for file in all_files:
            added = self.receipts_scans_repository.add_receipt(file)
            if added:
                new_files.append(file)
            else:
                print(f"File {file} already added.")
        if not new_files:
            print("No new files to process.")
            return
        total = len(new_files)
        for index, file in enumerate(new_files, start=1):
            success = self._process_single_file(file)
            if on_progress:
                on_progress(index=index, total=total, filename=file, status="done" if success else "failed")

    async def _run_production_async(self, on_progress=None):
        """Async version of _run_production: processes receipts in parallel (up to 5 at a time)."""
        CONCURRENT_LLM_CALLS = 5

        all_files = self.files_repository.list_input_files()
        if not all_files:
            print("No files to process.")
            return

        # Sequential dedup pass (fast DB inserts, ~ms each)
        new_files = []
        for file in all_files:
            added = self.receipts_scans_repository.add_receipt(file)
            if added:
                new_files.append(file)
            else:
                print(f"File {file} already added.")

        if not new_files:
            print("No new files to process.")
            return

        total = len(new_files)
        sem = asyncio.Semaphore(CONCURRENT_LLM_CALLS)
        db_lock = asyncio.Lock()
        # Thread-safe counter for 1-based progress index
        counter = {"value": 0}
        counter_lock = asyncio.Lock()

        async def _process_file(file: str):
            async with sem:
                try:
                    print(f"Processing file: {file}")
                    async with db_lock:
                        await asyncio.to_thread(
                            self.receipts_scans_repository.set_status,
                            file, ReceiptsScanStatus.PROCESSING,
                        )

                    preprocessed_image_path = await asyncio.to_thread(
                        self.preprocessing_service.preprocess_image, file
                    )

                    async with db_lock:
                        scan_id = await asyncio.to_thread(
                            self.receipts_scans_repository.get_scan_id_by_filename, file
                        )
                    object_key = f"receipts/{scan_id}_{_os_top.path.basename(file)}"

                    def _upload():
                        with open(preprocessed_image_path, "rb") as f:
                            image_data = f.read()
                        self.minio_service.upload_image(image_data, object_key, content_type="image/jpeg")

                    await asyncio.to_thread(_upload)
                    async with db_lock:
                        await asyncio.to_thread(
                            self.receipts_scans_repository.set_minio_key, file, object_key
                        )

                    # Dominant latency — run async OCR call outside the db_lock
                    ocr_result = await self.ocr_service.process_image_async(preprocessed_image_path)

                    async with db_lock:
                        await asyncio.to_thread(
                            self.receipts_scans_repository.set_result, file, ocr_result
                        )
                        await asyncio.to_thread(
                            self.receipts_scans_repository.set_status,
                            file, ReceiptsScanStatus.PROCESSED,
                        )

                    print(f"File {file} processed successfully.")

                    transaction_model = TransactionModel(**ocr_result)

                    vendor_mapping = await asyncio.to_thread(
                        self.vendors_service.process_vendor, transaction_model.vendor
                    )
                    async with db_lock:
                        await asyncio.to_thread(
                            self.vendors_repository.process_vendor_mapping, vendor_mapping
                        )
                    transaction_model = transaction_model.model_copy(
                        update={"vendor": vendor_mapping.vendor_name}
                    )

                    product_mappings = await asyncio.to_thread(
                        self.products_service.process_products, transaction_model.products
                    )
                    async with db_lock:
                        await asyncio.to_thread(
                            self.products_repository.process_product_mappings,
                            product_mappings.products,
                        )

                    category_candidates = await asyncio.to_thread(
                        self.categories_service.assign_category_candidates, transaction_model
                    )
                    async with db_lock:
                        await asyncio.to_thread(
                            self.receipts_scans_repository.set_category_candidates,
                            file, category_candidates,
                        )

                    status = "done"
                except Exception as e:
                    print(f"Error processing file {file}: {e}")
                    async with db_lock:
                        await asyncio.to_thread(
                            self.receipts_scans_repository.set_status,
                            file, ReceiptsScanStatus.FAILED, str(e),
                        )
                    status = "failed"

            if on_progress:
                async with counter_lock:
                    counter["value"] += 1
                    idx = counter["value"]
                on_progress(index=idx, total=total, filename=file, status=status)

        await asyncio.gather(*[_process_file(f) for f in new_files])

    # Ground Truth Methods (delegated to service)

    def create_ground_truth(self, filename: str, file_data: bytes) -> GroundTruthResponse:
        """Create a new ground truth entry by processing an uploaded image."""
        return self.ground_truth_service.create(filename, file_data)

    def update_ground_truth(self, entry_id: int, ground_truth: TransactionModel) -> GroundTruthResponse | None:
        """Update the ground truth data for an existing entry."""
        return self.ground_truth_service.update(entry_id, ground_truth)

    def get_ground_truth(self, entry_id: int) -> GroundTruthResponse | None:
        """Get a ground truth entry by ID."""
        return self.ground_truth_service.get(entry_id)

    def list_ground_truth(
        self, limit: int = 50, offset: int = 0, sort_by: str = "id", sort_dir: str = "desc"
    ) -> tuple[list[GroundTruthResponse], int]:
        """List ground truth entries, paginated."""
        return self.ground_truth_service.list(limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir)

    # ------------------------------------------------------------------
    # Receipts review / confirm API methods
    # ------------------------------------------------------------------

    def get_all_receipts(
        self,
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
    ) -> tuple[list[ReceiptScanListItem], int]:
        """Return receipt scans, paginated, with optional filters."""
        return self.receipts_scans_repository.get_all(
            status=status, limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir,
            search=search, vendor=vendor, product=product,
            date_from=date_from, date_to=date_to,
            total_min=total_min, total_max=total_max,
            tag=tag,
        )

    def get_receipt_status_counts(self) -> dict[str, int]:
        """Return count of receipt scans per status."""
        return self.receipts_scans_repository.get_status_counts()

    def get_receipt_by_id(self, scan_id: int) -> ReceiptScanDetail | None:
        """Return full scan detail, including confirmed transaction if present."""
        detail = self.receipts_scans_repository.get_by_id(scan_id)
        if detail is None:
            return None
        detail.transaction = self.transactions_repository.get_by_scan_id(scan_id)
        # Populate normalization suggestions from existing DB mappings so the UI
        # can pre-fill the "Normalized as" fields in the edit form.
        if detail.result:
            detail.vendor_normalization = (
                self.vendors_repository.get_normalized_name_by_alternative_name(detail.result.vendor)
            )
            detail.product_normalizations = {
                p.name: self.products_repository.get_normalized_name_by_alternative_name(p.name)
                for p in detail.result.products
            }
        # Attach bank link info if a confirmed receipt_transaction exists
        if detail.transaction is not None:
            link_data = self.bank_receipt_links_repository.get_bank_link_info(detail.transaction.id)
            if link_data:
                detail.bank_link = BankLinkInfo(**link_data)
            cash_link_data = self.cash_receipt_links_repository.get_cash_link_info(detail.transaction.id)
            if cash_link_data:
                detail.cash_link = CashLinkInfo(**cash_link_data)
        return detail

    def get_receipt_image_bytes(self, scan_id: int) -> bytes | None:
        """Download the preprocessed receipt image from MinIO."""
        detail = self.receipts_scans_repository.get_by_id(scan_id)
        if detail is None or detail.minio_object_key is None:
            return None
        return self.minio_service.download_image(detail.minio_object_key)

    def get_receipt_image_url(self, scan_id: int, expires_sec: int = 3600) -> str | None:
        """Return a presigned MinIO URL for the receipt image (direct browser access)."""
        detail = self.receipts_scans_repository.get_by_id(scan_id)
        if detail is None or detail.minio_object_key is None:
            return None
        return self.minio_service.get_presigned_url(detail.minio_object_key, expires_sec=expires_sec)

    def reupload_receipt_image(self, scan_id: int) -> bool:
        """
        Re-preprocess the source image from the input directory and re-upload it
        to MinIO, then update minio_object_key in the DB.

        Useful when the MinIO object is missing or was never stored (e.g. the
        scan was created but preprocessing failed mid-way).

        Returns True on success, False if the scan or source file was not found.
        """
        detail = self.receipts_scans_repository.get_by_id(scan_id)
        if detail is None:
            return False
        try:
            preprocessed_path = self.preprocessing_service.preprocess_image(detail.filename)
        except Exception as e:
            print(f"reupload_receipt_image: preprocessing failed for {detail.filename}: {e}")
            return False
        object_key = f"receipts/{scan_id}_{_os_top.path.basename(detail.filename)}"
        try:
            with open(preprocessed_path, "rb") as f:
                image_data = f.read()
            self.minio_service.upload_image(image_data, object_key, content_type="image/jpeg")
        except Exception as e:
            print(f"reupload_receipt_image: MinIO upload failed: {e}")
            return False
        self.receipts_scans_repository.set_minio_key(detail.filename, object_key)
        return True

    def get_ground_truth_image_bytes(self, entry_id: int) -> bytes | None:
        """Download the ground truth receipt image from MinIO."""
        entry = self.ground_truth_repository.get_by_id(entry_id)
        if entry is None:
            return None
        return self.minio_service.download_image(entry.minio_object_key)

    def confirm_receipt(self, scan_id: int, request: ConfirmReceiptRequest) -> ReceiptScanDetail | None:
        """
        Confirm receipt categories.

        1. Load OCR result for raw data.
        2. Apply any field overrides supplied in the request (vendor, date, total, products).
        3. Persist the (possibly updated) result back to the DB so the stored data stays accurate.
        4. Look up vendor_id via vendors_alternative_names.
        5. Insert receipt_transactions row.
        6. For each product look up product_id, insert receipt_transaction_items row.
        7. Set scan status to DONE.
        """
        detail = self.receipts_scans_repository.get_by_id(scan_id)
        if detail is None or detail.result is None:
            return None

        tx_model = detail.result

        # Apply optional field overrides before creating the transaction
        overrides: dict = {}
        if request.vendor is not None:
            overrides["vendor"] = request.vendor
        if request.date is not None:
            overrides["date"] = request.date
        if request.total is not None:
            overrides["total"] = request.total
        if request.products is not None:
            overrides["products"] = request.products
        if overrides:
            tx_model = tx_model.model_copy(update=overrides)
            self.receipts_scans_repository.set_result_by_id(scan_id, tx_model.model_dump())

        vendor_id = None
        if request.normalized_vendor:
            # The user supplied a normalized vendor name — look it up or create it, then
            # link the raw receipt name as an alternative name so future receipts resolve
            # automatically.
            vendor_id = self.vendors_repository.get_vendor_by_name(request.normalized_vendor)
            if vendor_id is None:
                vendor_id = self.vendors_repository.insert_vendor(request.normalized_vendor)
            if vendor_id is not None:
                self.vendors_repository.insert_alternative_name(tx_model.vendor, vendor_id)
        else:
            vendor_id = self.transactions_repository.lookup_vendor_id(tx_model.vendor)

        import datetime as _dt
        try:
            tx_date = _dt.date.fromisoformat(tx_model.date)
        except Exception:
            tx_date = _dt.date.today()

        transaction_id = self.transactions_repository.create_transaction(
            scan_id=scan_id,
            vendor_id=vendor_id,
            raw_vendor_name=tx_model.vendor,
            transaction_date=tx_date,
            total=tx_model.total,
        )
        if transaction_id == -1:
            return None

        for product in tx_model.products:
            normalized_product_name = (
                request.normalized_products.get(product.name)
                if request.normalized_products
                else None
            )
            if normalized_product_name:
                # Look up or create the normalized product and link the raw name.
                product_id = self.products_repository.get_product_by_name(normalized_product_name)
                if product_id is None:
                    product_id = self.products_repository.insert_product(normalized_product_name)
                if product_id is not None:
                    self.products_repository.insert_alternative_name(product.name, product_id)
            else:
                product_id = self.transactions_repository.lookup_product_id(product.name)
            category_id = request.product_categories.get(product.name)
            if category_id is None:
                continue
            self.transactions_repository.create_transaction_item(
                transaction_id=transaction_id,
                product_id=product_id,
                raw_product_name=product.name,
                category_id=category_id,
                quantity=product.quantity,
                unit_price=product.unit_price,
                price=product.price,
            )

        self.receipts_scans_repository.set_status_done(scan_id)

        # Collect prompt analytics
        self._save_prompt_analytics(scan_id, detail, request, tx_model)

        # Auto-save as ground truth (skip silently if already present)
        self.ground_truth_service.create_from_confirmed_receipt(
            filename=detail.filename,
            minio_object_key=detail.minio_object_key,
            transaction=tx_model,
        )

        return self.get_receipt_by_id(scan_id)

    def _save_prompt_analytics(
        self,
        scan_id: int,
        detail,
        request: ConfirmReceiptRequest,
        tx_model,
    ) -> None:
        """Compute and persist prompt quality analytics for a confirmed receipt."""
        try:
            # --- Category corrections ---
            category_corrections = []
            candidates_raw = detail.categories_candidates or {}
            # Build a flat lookup: product_name -> top candidate
            top_candidate_map: dict[str, dict] = {}
            for entry in candidates_raw.get("category_candidates", []):
                product_name = entry.get("product_name", "")
                candidates = entry.get("category_candidates", [])
                if candidates:
                    top = max(candidates, key=lambda c: c.get("category_score", 0))
                    top_candidate_map[product_name] = top

            for raw_name, user_cat_id in request.product_categories.items():
                top = top_candidate_map.get(raw_name)
                if top is None:
                    continue
                ai_cat_id = top.get("category_id")
                if ai_cat_id != user_cat_id:
                    category_corrections.append({
                        "raw_product_name": raw_name,
                        "ai_category_id": ai_cat_id,
                        "ai_category_name": top.get("category_name", ""),
                        "ai_confidence": top.get("category_score", 0.0),
                        "user_category_id": user_cat_id,
                        "user_category_name": "",  # resolved below if needed
                    })

            # Resolve user category names from the DB
            if category_corrections:
                all_categories = {c.id: c.name for c in self.categories_repository.get_all_expense_categories()}
                for corr in category_corrections:
                    corr["user_category_name"] = all_categories.get(corr["user_category_id"], "")

            # --- Product name corrections ---
            product_name_corrections = []
            ai_normalizations = detail.product_normalizations or {}
            user_normalizations = request.normalized_products or {}
            for raw_name, user_norm in user_normalizations.items():
                ai_norm = ai_normalizations.get(raw_name)
                if ai_norm and user_norm and ai_norm.lower() != user_norm.lower():
                    product_name_corrections.append({
                        "raw_product_name": raw_name,
                        "ai_normalized_name": ai_norm,
                        "user_normalized_name": user_norm,
                    })

            # --- Product count diff ---
            ocr_products = detail.result.products if detail.result else []
            confirmed_products = tx_model.products
            ocr_count = len(ocr_products)
            confirmed_count = len(confirmed_products)

            ocr_names = {p.name for p in ocr_products}
            confirmed_names = {p.name for p in confirmed_products}
            products_added = list(confirmed_names - ocr_names)
            products_removed = list(ocr_names - confirmed_names)

            details = {
                "category_corrections": category_corrections,
                "product_name_corrections": product_name_corrections,
                "products_added": products_added,
                "products_removed": products_removed,
            }

            vendor_name = tx_model.vendor if tx_model else None

            self.prompt_analytics_repository.upsert(
                scan_id=scan_id,
                vendor_name=vendor_name,
                category_corrections_count=len(category_corrections),
                product_name_corrections_count=len(product_name_corrections),
                ocr_product_count=ocr_count,
                confirmed_product_count=confirmed_count,
                details=details,
            )
        except Exception as e:
            # Analytics must never break confirmation
            print("Warning: failed to save prompt analytics:", e)

    def get_prompt_analytics(self) -> PromptAnalyticsSummary:
        """Return aggregated prompt analytics summary with recent rows."""
        summary = self.prompt_analytics_repository.get_summary()
        recent = self.prompt_analytics_repository.get_all(limit=50, offset=0)
        return PromptAnalyticsSummary(
            total_receipts=summary.get("total_receipts", 0),
            total_category_corrections=summary.get("total_category_corrections", 0),
            total_product_name_corrections=summary.get("total_product_name_corrections", 0),
            receipts_with_added_products=summary.get("receipts_with_added_products", 0),
            receipts_with_removed_products=summary.get("receipts_with_removed_products", 0),
            receipts_with_product_count_mismatch=summary.get("receipts_with_product_count_mismatch", 0),
            avg_category_corrections=summary.get("avg_category_corrections", 0.0),
            avg_product_name_corrections=summary.get("avg_product_name_corrections", 0.0),
            avg_ocr_product_count=summary.get("avg_ocr_product_count", 0.0),
            top_category_confusions=summary.get("top_category_confusions", []),
            top_product_name_corrections=summary.get("top_product_name_corrections", []),
            recent=recent,
        )

    def reopen_receipt(self, scan_id: int) -> ReceiptScanDetail | None:
        """
        Reopen a confirmed receipt for editing.

        Deletes the existing transaction rows and resets status back to TO_CONFIRM,
        so the user can correct OCR-sourced fields and categories before re-confirming.
        """
        detail = self.receipts_scans_repository.get_by_id(scan_id)
        if detail is None:
            return None
        self.transactions_repository.delete_by_scan_id(scan_id)
        self.receipts_scans_repository.set_status_to_confirm_by_id(scan_id)
        return self.get_receipt_by_id(scan_id)

    def update_transaction_item(
        self, item_id: int, request: UpdateTransactionItemRequest
    ) -> ReceiptTransactionItem | None:
        """Update individual fields on a confirmed receipt transaction item."""
        fields = request.model_dump(exclude_none=True)
        if not fields:
            return None
        return self.transactions_repository.update_transaction_item(item_id, fields)

    def delete_transaction_item(self, item_id: int) -> bool:
        """Delete a single confirmed receipt transaction item."""
        return self.transactions_repository.delete_transaction_item(item_id)

    def delete_receipt(self, scan_id: int) -> bool:
        """
        Permanently delete a receipt scan.

        Removes the confirmed transaction rows (and their bank links / items via
        ON DELETE CASCADE), the MinIO preprocessed image, and finally the
        receipts_scans row itself.
        """
        detail = self.receipts_scans_repository.get_by_id(scan_id)
        if detail is None:
            return False
        # Remove confirmed transaction rows (cascades to items and bank links)
        self.transactions_repository.delete_by_scan_id(scan_id)
        # Remove preprocessed image from object storage
        if detail.minio_object_key:
            self.minio_service.delete_image(detail.minio_object_key)
        # Remove the scan row itself
        return self.receipts_scans_repository.delete_scan_by_id(scan_id)

    def retry_receipt(self, scan_id: int) -> bool:
        """
        Re-run the full OCR pipeline for a single receipt.

        Resets the scan state to 'pending' and re-processes the source file from
        the input directory through preprocessing, OCR, vendor/product
        normalisation and category candidate assignment.
        Returns True on success, False if the scan was not found or the source
        file is missing.
        """
        filename = self.receipts_scans_repository.reset_for_retry(scan_id)
        if filename is None:
            return False
        self._process_single_file(filename)
        return True

    def _process_single_file(self, filename: str) -> bool:
        """
        Run the production processing pipeline for one specific file.

        Unlike _run_production this method does NOT call add_receipt — the
        receipts_scans row must already exist.  Used by both _run_production
        (batch loop) and retry_receipt (single-scan retry).

        Returns True on success, False on failure (status set to FAILED).
        """
        try:
            print(f"Processing file: {filename}")
            self.receipts_scans_repository.set_status(filename, ReceiptsScanStatus.PROCESSING)
            preprocessed_image_path = self.preprocessing_service.preprocess_image(filename)

            scan_id = self.receipts_scans_repository.get_scan_id_by_filename(filename)
            object_key = f"receipts/{scan_id}_{_os_top.path.basename(filename)}"
            with open(preprocessed_image_path, "rb") as f:
                image_data = f.read()
            self.minio_service.upload_image(image_data, object_key, content_type="image/jpeg")
            self.receipts_scans_repository.set_minio_key(filename, object_key)

            ocr_result = self.ocr_service.process_image(preprocessed_image_path)
            self.receipts_scans_repository.set_result(filename, ocr_result)
            self.receipts_scans_repository.set_status(filename, ReceiptsScanStatus.PROCESSED)
            print(f"File {filename} processed successfully.")

            transaction_model = TransactionModel(**ocr_result)

            vendor_mapping = self.vendors_service.process_vendor(transaction_model.vendor)
            self.vendors_repository.process_vendor_mapping(vendor_mapping)
            transaction_model = transaction_model.model_copy(
                update={"vendor": vendor_mapping.vendor_name}
            )

            product_mappings = self.products_service.process_products(transaction_model.products)
            self.products_repository.process_product_mappings(product_mappings.products)

            category_candidates = self.categories_service.assign_category_candidates(transaction_model)
            self.receipts_scans_repository.set_category_candidates(filename, category_candidates)
            return True
        except Exception as e:
            print(f"Error processing file {filename}: {e}")
            self.receipts_scans_repository.set_status(filename, ReceiptsScanStatus.FAILED, str(e))
            return False

    def get_all_expense_categories(self) -> list[CategoryItem]:
        """Return all expense categories."""
        return self.categories_repository.get_all_expense_categories()

    def create_category(self, name: str, parent_id: int | None) -> CategoryItem | None:
        """Create a new expense category."""
        return self.categories_repository.create_category(name, parent_id)

    def get_all_evaluation_runs(
        self, limit: int = 50, offset: int = 0, sort_by: str = "id", sort_dir: str = "desc"
    ) -> tuple[list[EvaluationRunListItem], int]:
        """Return evaluation runs, paginated, newest first."""
        return self.evaluations_repository.get_all_runs(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir
        )

    def get_evaluation_run(self, run_id: int) -> EvaluationRunDetail | None:
        """Return a single evaluation run with all per-file results."""
        return self.evaluations_repository.get_run_with_results(run_id)

    # ------------------------------------------------------------------
    # Bank transactions
    # ------------------------------------------------------------------

    def import_bank_csv(self, data: bytes) -> tuple[BankImportResult, list[int]]:
        """Parse a Pekao CSV and insert new rows. Returns result + IDs pending categorization.

        LLM categorization is NOT run here — the caller should dispatch it as a
        background Celery task using the returned list of new IDs.
        """
        rows = self.bank_csv_parser.parse_bytes(data)
        if not rows:
            return BankImportResult(imported=0, duplicates=0, errors=0), []

        inserted, duplicates = self.bank_transactions_repository.insert_transactions(rows)

        # Collect IDs that still need LLM categorization
        new_ids = self.bank_transactions_repository.get_new_ids_for_categorization()
        return BankImportResult(imported=inserted, duplicates=duplicates, errors=0), new_ids

    def categorize_bank_transactions(self, transaction_ids: list[int]) -> None:
        """Run LLM categorization for the given bank transaction IDs."""
        for tx_id in transaction_ids:
            try:
                tx = self.bank_transactions_repository.get_by_id(tx_id)
                if tx is None:
                    continue
                candidates = self.bank_categorization_service.assign_candidates(tx)
                self.bank_transactions_repository.update_candidates(tx_id, candidates)
            except Exception as e:
                print(f"LLM categorization failed for bank_transaction {tx_id}: {e}")

    def get_all_bank_transactions(
        self, limit: int = 50, offset: int = 0,
        sort_by: str = "booking_date", sort_dir: str = "desc",
        tag: str | None = None,
    ) -> tuple[list[BankTransactionListItem], int]:
        return self.bank_transactions_repository.get_list(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir,
            tag=tag,
        )

    def get_bank_transaction_by_id(self, tx_id: int) -> BankTransactionDetail | None:
        detail = self.bank_transactions_repository.get_by_id(tx_id)
        if detail is None:
            return None
        link_data = self.bank_receipt_links_repository.get_receipt_link_info(tx_id)
        if link_data:
            detail.receipt_link = ReceiptLinkInfo(**link_data)
        return detail

    def update_bank_transaction_category(
        self, tx_id: int, request: UpdateBankTransactionCategoryRequest
    ) -> BankTransactionDetail | None:
        """Update the category of a bank transaction (skip if receipt-linked)."""
        link_data = self.bank_receipt_links_repository.get_receipt_link_info(tx_id)
        if not link_data:
            self.bank_transactions_repository.update_category(tx_id, request.category_id)
        return self.get_bank_transaction_by_id(tx_id)

    # ------------------------------------------------------------------
    # Bank ↔ Receipt linking
    # ------------------------------------------------------------------

    def get_receipt_candidates_for_bank_tx(
        self, tx_id: int
    ) -> list[ReceiptCandidateItem]:
        """Return receipt_transaction candidates that match a bank transaction."""
        candidates = self.bank_receipt_links_repository.find_receipt_candidates(tx_id)
        return [
            ReceiptCandidateItem(
                receipt_transaction_id=c.receipt_transaction_id,
                scan_id=c.scan_id,
                scan_filename=c.scan_filename,
                vendor_name=c.vendor_name,
                date=c.date,
                total=c.total,
                match_score=c.match_score,
            )
            for c in candidates
        ]

    def get_bank_tx_candidates_for_receipt(
        self, scan_id: int
    ) -> list[BankTxCandidateItem]:
        """Return bank_transaction candidates that match the receipt_transaction for a scan."""
        tx = self.transactions_repository.get_by_scan_id(scan_id)
        if tx is None:
            return []
        candidates = self.bank_receipt_links_repository.find_bank_tx_candidates(tx.id)
        return [
            BankTxCandidateItem(
                bank_transaction_id=c.bank_transaction_id,
                counterparty=c.counterparty,
                booking_date=c.booking_date,
                amount=c.amount,
                match_score=c.match_score,
            )
            for c in candidates
        ]

    def link_bank_to_receipt(
        self, tx_id: int, request: LinkReceiptRequest
    ) -> BankTransactionDetail | None:
        """Create a link between a bank transaction and a receipt transaction."""
        ok = self.bank_receipt_links_repository.create_link(
            bank_transaction_id=tx_id,
            receipt_transaction_id=request.receipt_transaction_id,
        )
        if not ok:
            return None  # conflict — already linked
        # Merge tags from both sides after linking
        link_info = self.bank_receipt_links_repository.get_receipt_link_info(tx_id)
        if link_info:
            scan_id = link_info["scan_id"]
            scan_tags = self.receipts_scans_repository.get_tags_for_scan(scan_id)
            tx_tags = self.bank_transactions_repository.get_tags_for_tx(tx_id)
            merged = sorted(set(scan_tags) | set(tx_tags))
            if merged != sorted(set(scan_tags)) or merged != sorted(set(tx_tags)):
                self.receipts_scans_repository.update_tags(scan_id, merged)
                self.bank_transactions_repository.update_tags(tx_id, merged)
        return self.get_bank_transaction_by_id(tx_id)

    def unlink_bank_transaction(self, tx_id: int) -> BankTransactionDetail | None:
        """Remove the link from a bank transaction to any receipt."""
        self.bank_receipt_links_repository.delete_link_by_bank_tx(tx_id)
        return self.get_bank_transaction_by_id(tx_id)

    # ------------------------------------------------------------------
    # Cash transactions
    # ------------------------------------------------------------------

    def create_cash_transaction(
        self, data: CashTransactionCreate
    ) -> CashTransactionDetail | None:
        """Create a manual cash transaction."""
        import datetime as _dt
        booking_date = _dt.date.fromisoformat(data.booking_date)
        tx_id = self.cash_transactions_repository.insert_transaction(
            booking_date=booking_date,
            amount=data.amount,
            description=data.description,
            category_id=data.category_id,
            vendor_id=data.vendor_id,
            source="manual",
        )
        if tx_id is None:
            return None
        return self.get_cash_transaction_by_id(tx_id)

    def create_cash_transaction_from_receipt(
        self, scan_id: int
    ) -> CashTransactionDetail | None:
        """Auto-create a cash transaction from a confirmed receipt scan."""
        tx = self.transactions_repository.get_by_scan_id(scan_id)
        if tx is None:
            return None  # receipt not confirmed yet
        # Re-read scan to get tags
        scan = self.receipts_scans_repository.get_by_id(scan_id)
        # Derive category from first item (most common)
        category_id: int | None = None
        if tx.items:
            category_id = tx.items[0].category_id
        # Amount is negative (expense) — receipts track spend
        amount = -abs(tx.total)
        tx_id = self.cash_transactions_repository.insert_transaction(
            booking_date=__import__("datetime").date.fromisoformat(tx.date),
            amount=amount,
            description=None,
            category_id=category_id,
            vendor_id=tx.vendor_id,
            source="receipt",
            receipt_scan_id=scan_id,
        )
        if tx_id is None:
            return None
        # Link to receipt_transaction
        self.cash_receipt_links_repository.create_link(tx_id, tx.id)
        # Copy tags from the scan if any
        if scan and scan.tags:
            self.cash_transactions_repository.update_tags(tx_id, scan.tags)
        return self.get_cash_transaction_by_id(tx_id)

    def get_all_cash_transactions(
        self, limit: int = 50, offset: int = 0,
        sort_by: str = "booking_date", sort_dir: str = "desc",
        tag: str | None = None,
    ) -> tuple[list[CashTransactionListItem], int]:
        return self.cash_transactions_repository.get_list(
            limit=limit, offset=offset, sort_by=sort_by, sort_dir=sort_dir,
            tag=tag,
        )

    def get_cash_transaction_by_id(self, tx_id: int) -> CashTransactionDetail | None:
        detail = self.cash_transactions_repository.get_by_id(tx_id)
        if detail is None:
            return None
        link_data = self.cash_receipt_links_repository.get_receipt_link_info(tx_id)
        if link_data:
            detail.receipt_link = CashReceiptLinkInfo(**link_data)
        return detail

    def update_cash_transaction(
        self, tx_id: int, data: CashTransactionUpdate
    ) -> CashTransactionDetail | None:
        import datetime as _dt
        booking_date = _dt.date.fromisoformat(data.booking_date) if data.booking_date else None
        self.cash_transactions_repository.update(
            tx_id,
            booking_date=booking_date,
            description=data.description,
            amount=data.amount,
            category_id=data.category_id,
            vendor_id=data.vendor_id,
        )
        return self.get_cash_transaction_by_id(tx_id)

    def delete_cash_transaction(self, tx_id: int) -> bool:
        return self.cash_transactions_repository.delete(tx_id)

    def delete_bank_transaction(self, tx_id: int) -> bool:
        return self.bank_transactions_repository.delete(tx_id)

    def update_cash_transaction_category(
        self, tx_id: int, request: UpdateCashTransactionCategoryRequest
    ) -> CashTransactionDetail | None:
        """Update the category of a cash transaction (skip if receipt-linked)."""
        link_data = self.cash_receipt_links_repository.get_receipt_link_info(tx_id)
        if not link_data:
            self.cash_transactions_repository.update_category(tx_id, request.category_id)
        return self.get_cash_transaction_by_id(tx_id)

    def get_receipt_candidates_for_cash_tx(
        self, tx_id: int
    ) -> list[ReceiptCandidateItem]:
        candidates = self.cash_receipt_links_repository.find_receipt_candidates(tx_id)
        return [
            ReceiptCandidateItem(
                receipt_transaction_id=c["receipt_transaction_id"],
                scan_id=c["scan_id"],
                scan_filename=c["scan_filename"],
                vendor_name=c["vendor_name"],
                date=c["date"],
                total=c["total"],
                match_score=c["match_score"],
            )
            for c in candidates
        ]

    def get_cash_tx_candidates_for_receipt(
        self, scan_id: int
    ) -> list[CashTxCandidateItem]:
        tx = self.transactions_repository.get_by_scan_id(scan_id)
        if tx is None:
            return []
        candidates = self.cash_receipt_links_repository.find_cash_tx_candidates(tx.id)
        return [
            CashTxCandidateItem(
                cash_transaction_id=c["cash_transaction_id"],
                description=c["description"],
                booking_date=c["booking_date"],
                amount=c["amount"],
                match_score=c["match_score"],
            )
            for c in candidates
        ]

    def link_cash_to_receipt(
        self, tx_id: int, request: LinkCashReceiptRequest
    ) -> CashTransactionDetail | None:
        ok = self.cash_receipt_links_repository.create_link(
            cash_transaction_id=tx_id,
            receipt_transaction_id=request.receipt_transaction_id,
        )
        if not ok:
            return None
        return self.get_cash_transaction_by_id(tx_id)

    def unlink_cash_transaction(self, tx_id: int) -> CashTransactionDetail | None:
        self.cash_receipt_links_repository.delete_link_by_cash_tx(tx_id)
        return self.get_cash_transaction_by_id(tx_id)

    def update_receipt_tags(self, scan_id: int, tags: list[str]) -> None:
        """Update tags for a receipt scan and propagate to any linked bank/cash transaction."""
        self.receipts_scans_repository.update_tags(scan_id, tags)
        bank_tx_id = self.bank_receipt_links_repository.get_bank_tx_id_for_scan(scan_id)
        if bank_tx_id is not None:
            bank_tags = self.bank_transactions_repository.get_tags_for_tx(bank_tx_id)
            merged = sorted(set(tags) | set(bank_tags))
            self.receipts_scans_repository.update_tags(scan_id, merged)
            self.bank_transactions_repository.update_tags(bank_tx_id, merged)
        cash_tx_id = self.cash_receipt_links_repository.get_cash_tx_id_for_scan(scan_id)
        if cash_tx_id is not None:
            cash_tags = self.cash_transactions_repository.get_tags_for_tx(cash_tx_id)
            merged = sorted(set(tags) | set(cash_tags))
            self.receipts_scans_repository.update_tags(scan_id, merged)
            self.cash_transactions_repository.update_tags(cash_tx_id, merged)

    def update_cash_transaction_tags(self, tx_id: int, tags: list[str]) -> None:
        """Update tags for a cash transaction and propagate to linked receipt scan."""
        self.cash_transactions_repository.update_tags(tx_id, tags)
        link_data = self.cash_receipt_links_repository.get_receipt_link_info(tx_id)
        if link_data is not None:
            scan_id = link_data["scan_id"]
            scan_tags = self.receipts_scans_repository.get_tags_for_scan(scan_id)
            merged = sorted(set(tags) | set(scan_tags))
            self.cash_transactions_repository.update_tags(tx_id, merged)
            self.receipts_scans_repository.update_tags(scan_id, merged)

    def update_bank_transaction_tags(self, tx_id: int, tags: list[str]) -> None:
        """Update tags for a bank transaction and propagate to linked receipt."""
        self.bank_transactions_repository.update_tags(tx_id, tags)
        link_info = self.bank_receipt_links_repository.get_receipt_link_info(tx_id)
        if link_info is not None:
            scan_id = link_info["scan_id"]
            scan_tags = self.receipts_scans_repository.get_tags_for_scan(scan_id)
            merged = sorted(set(tags) | set(scan_tags))
            self.bank_transactions_repository.update_tags(tx_id, merged)
            self.receipts_scans_repository.update_tags(scan_id, merged)

    # ------------------------------------------------------------------
    # Unified transactions
    # ------------------------------------------------------------------

    def get_unified_transactions(
        self,
        status=None,
        source_type=None,
        date_from=None,
        date_to=None,
        category_id=None,
        tag=None,
        search=None,
        amount_min=None,
        amount_max=None,
        direction=None,
        sort_by="date",
        sort_dir="desc",
        limit=50,
        offset=0,
    ) -> tuple[list[UnifiedTransaction], int]:
        return self.unified_transactions_repository.get_list(
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

    def get_transactions_analytics(
        self, date_from=None, date_to=None
    ) -> AnalyticsSummary:
        return self.unified_transactions_repository.get_analytics(
            date_from=date_from, date_to=date_to
        )

    def get_all_tags(self) -> list[str]:
        """Return all distinct tags used across receipts_scans, bank_transactions, and cash_transactions."""
        if not self.receipts_scans_repository.conn:
            return []
        try:
            with self.receipts_scans_repository.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT DISTINCT tag FROM (
                        SELECT unnest(tags) AS tag FROM receipts_scans
                        UNION
                        SELECT unnest(tags) AS tag FROM bank_transactions
                        UNION
                        SELECT unnest(tags) AS tag FROM cash_transactions
                    ) t
                    WHERE tag IS NOT NULL AND tag <> ''
                    ORDER BY tag
                    """
                )
                return [r[0] for r in cur.fetchall()]
        except Exception as e:
            print(f"App.get_all_tags error: {e}")
            return []

    def dispose(self):
        self.files_repository.dispose()
        self.receipts_scans_repository.dispose()
        self.evaluations_repository.dispose()
        self.ground_truth_repository.dispose()
        self.vendors_repository.dispose()
        self.products_repository.dispose()
        self.transactions_repository.dispose()
        self.categories_repository.dispose()
        self.bank_transactions_repository.dispose()
        self.bank_receipt_links_repository.dispose()
        self.cash_transactions_repository.dispose()
        self.cash_receipt_links_repository.dispose()
        self.ocr_service.dispose()
        # unified_transactions_repository has no own connection — no dispose needed
        self.minio_service.dispose()
        self.vendors_service.dispose()
        self.products_service.dispose()
        self.evaluation_service.dispose()
        self.ground_truth_service.dispose()
        self.eye_budget_db_context.dispose()
        print("All resources disposed.")
