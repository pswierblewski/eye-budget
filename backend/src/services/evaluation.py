import asyncio
import os
import time

from ..data import (
    TransactionModel,
    EvaluationMetrics,
    EvaluationResult,
    EvaluationRunSummary,
    GroundTruthEntry,
)
from ..repositories.evaluations import EvaluationsRepository
from ..repositories.ground_truth import GroundTruthRepository
from .minio_storage import MinioStorageService
from .preprocessing import PreprocessingService
from .ocr import OCRService


class EvaluationService:
    """Service for running evaluations against ground truth data."""
    
    def __init__(
        self,
        evaluations_repository: EvaluationsRepository,
        ground_truth_repository: GroundTruthRepository,
        minio_service: MinioStorageService,
        preprocessing_service: PreprocessingService,
        ocr_service: OCRService
    ):
        self.evaluations_repository = evaluations_repository
        self.ground_truth_repository = ground_truth_repository
        self.minio_service = minio_service
        self.preprocessing_service = preprocessing_service
        self.ocr_service = ocr_service

    def run_evaluation(self, on_progress=None) -> EvaluationRunSummary:
        """Run evaluation mode: process ground truth entries and compare OCR results."""
        model_used = self.ocr_service.model
        
        # Create evaluation run
        run_id = self.evaluations_repository.create_run(
            model_used=model_used,
            config={
                "source": "ground_truth",
                "model": self.ocr_service.model,
                "prompt": self.ocr_service.prompt,
                "reasoning_effort": "medium",
            }
        )
        
        # Load all ground truth entries
        ground_truth_entries = self.ground_truth_repository.get_all()
        if not ground_truth_entries:
            print("No ground truth entries to evaluate.")
            return self._create_empty_summary(run_id, model_used)
        
        results: list[EvaluationResult] = []
        total = len(ground_truth_entries)
        
        for index, entry in enumerate(ground_truth_entries, start=1):
            result = self._evaluate_ground_truth_entry(entry)
            results.append(result)
            
            # Store result in database
            self.evaluations_repository.add_result(run_id, result)

            if on_progress:
                on_progress(
                    index=index,
                    total=total,
                    filename=entry.filename,
                    success=result.success,
                )
        
        # Calculate summary statistics
        summary = self._calculate_summary(run_id, model_used, results)
        
        # Update run with summary
        self.evaluations_repository.update_run_summary(run_id, summary)
        
        return summary

    async def run_evaluation_async(self, on_progress=None) -> EvaluationRunSummary:
        """Async version of run_evaluation: processes ground truth entries in parallel."""
        CONCURRENT_LLM_CALLS = 5

        model_used = self.ocr_service.model

        # Create evaluation run (synchronous, once)
        run_id = self.evaluations_repository.create_run(
            model_used=model_used,
            config={
                "source": "ground_truth",
                "model": self.ocr_service.model,
                "prompt": self.ocr_service.prompt,
                "reasoning_effort": "medium",
            },
        )

        ground_truth_entries = self.ground_truth_repository.get_all()
        if not ground_truth_entries:
            print("No ground truth entries to evaluate.")
            return self._create_empty_summary(run_id, model_used)

        total = len(ground_truth_entries)
        sem = asyncio.Semaphore(CONCURRENT_LLM_CALLS)
        db_lock = asyncio.Lock()
        counter = {"value": 0}
        counter_lock = asyncio.Lock()
        results_store: list[EvaluationResult | None] = [None] * total

        async def _evaluate_one(index: int, entry: GroundTruthEntry):
            async with sem:
                # Download + preprocess (IO-bound) outside db_lock
                temp_path = await asyncio.to_thread(
                    self.minio_service.get_temp_file, entry.minio_object_key
                )
                preprocessed_path = await asyncio.to_thread(
                    self.preprocessing_service.preprocess_image, temp_path
                )
                try:
                    # Dominant latency — async OCR call
                    result = await self._evaluate_ground_truth_entry_async(
                        entry, preprocessed_path
                    )
                finally:
                    await asyncio.to_thread(
                        lambda: os.remove(temp_path) if os.path.exists(temp_path) else None
                    )

            results_store[index] = result

            async with db_lock:
                await asyncio.to_thread(
                    self.evaluations_repository.add_result, run_id, result
                )

            if on_progress:
                async with counter_lock:
                    counter["value"] += 1
                    idx = counter["value"]
                on_progress(
                    index=idx,
                    total=total,
                    filename=entry.filename,
                    success=result.success,
                )

        await asyncio.gather(
            *[_evaluate_one(i, entry) for i, entry in enumerate(ground_truth_entries)]
        )

        results = [r for r in results_store if r is not None]
        summary = self._calculate_summary(run_id, model_used, results)
        self.evaluations_repository.update_run_summary(run_id, summary)
        return summary

    async def _evaluate_ground_truth_entry_async(
        self, entry: GroundTruthEntry, preprocessed_path: str
    ) -> EvaluationResult:
        """Async version: reuses an already-preprocessed image path."""
        start_time = time.time()
        try:
            print(f"Evaluating ground truth entry: {entry.filename}")
            ocr_result = await self.ocr_service.process_image_async(preprocessed_path)
            transaction = TransactionModel(**ocr_result)
            processing_time_ms = int((time.time() - start_time) * 1000)
            metrics = self.calculate_metrics(
                transaction, processing_time_ms, ground_truth=entry.ground_truth
            )
            print(f"Ground truth entry {entry.filename} evaluated successfully.")
            return EvaluationResult(
                filename=entry.filename,
                success=True,
                metrics=metrics,
                transaction=transaction,
            )
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            print(f"Error evaluating ground truth entry {entry.filename}: {e}")
            return EvaluationResult(
                filename=entry.filename,
                success=False,
                error_message=str(e),
            )

    def _evaluate_ground_truth_entry(self, entry: GroundTruthEntry) -> EvaluationResult:
        """Process a ground truth entry and return evaluation result with accuracy metrics."""
        start_time = time.time()
        temp_path = None
        
        try:
            print(f"Evaluating ground truth entry: {entry.filename}")
            
            # Download image from MinIO to temp file
            temp_path = self.minio_service.get_temp_file(entry.minio_object_key)
            
            # Run OCR preprocessing and processing
            preprocessed_path = self.preprocessing_service.preprocess_image(temp_path)
            ocr_result = self.ocr_service.process_image(preprocessed_path)
            transaction = TransactionModel(**ocr_result)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Calculate metrics with ground truth comparison
            metrics = self.calculate_metrics(
                transaction, 
                processing_time_ms, 
                ground_truth=entry.ground_truth
            )
            
            print(f"Ground truth entry {entry.filename} evaluated successfully.")
            return EvaluationResult(
                filename=entry.filename,
                success=True,
                metrics=metrics,
                transaction=transaction
            )
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            print(f"Error evaluating ground truth entry {entry.filename}: {e}")
            return EvaluationResult(
                filename=entry.filename,
                success=False,
                error_message=str(e)
            )
        finally:
            # Cleanup temp file
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)

    def calculate_metrics(
        self, 
        transaction: TransactionModel, 
        processing_time_ms: int,
        ground_truth: TransactionModel | None = None
    ) -> EvaluationMetrics:
        """Calculate evaluation metrics for a transaction, optionally comparing to ground truth."""
        # Field extraction metrics
        has_vendor = bool(transaction.vendor)
        has_date = bool(transaction.date)
        has_total = transaction.total is not None
        has_title = bool(transaction.title)
        has_products = len(transaction.products) > 0
        
        fields_extracted = sum([has_vendor, has_date, has_total, has_title, has_products])
        fields_total = 5
        field_completeness = fields_extracted / fields_total
        
        # Consistency metrics
        products_sum = sum(p.price for p in transaction.products)
        extracted_total = transaction.total
        total_difference = abs(products_sum - extracted_total)
        is_consistent = total_difference < 0.01
        
        # Ground truth comparison metrics (if ground truth is provided)
        vendor_correct = None
        date_correct = None
        total_correct = None
        total_accuracy = None
        product_count_correct = None
        products_accuracy = None
        
        if ground_truth:
            # Vendor comparison (case-insensitive)
            vendor_correct = transaction.vendor.lower().strip() == ground_truth.vendor.lower().strip()
            
            # Date comparison
            date_correct = transaction.date == ground_truth.date
            
            # Total comparison (within tolerance of 0.01)
            total_diff = abs(transaction.total - ground_truth.total)
            total_correct = total_diff < 0.01
            
            # Total accuracy as percentage
            if ground_truth.total != 0:
                total_accuracy = max(0, 1.0 - (total_diff / abs(ground_truth.total)))
            else:
                total_accuracy = 1.0 if transaction.total == 0 else 0.0
            
            # Product count comparison
            product_count_correct = len(transaction.products) == len(ground_truth.products)
            
            # Products accuracy - match products by name and price
            products_accuracy = self._calculate_products_accuracy(
                transaction.products, 
                ground_truth.products
            )
        
        return EvaluationMetrics(
            processing_time_ms=processing_time_ms,
            fields_extracted=fields_extracted,
            field_completeness=field_completeness,
            product_count=len(transaction.products),
            has_vendor=has_vendor,
            has_date=has_date,
            has_total=has_total,
            products_sum=round(products_sum, 2),
            extracted_total=extracted_total,
            total_difference=round(total_difference, 2),
            is_consistent=is_consistent,
            vendor_correct=vendor_correct,
            date_correct=date_correct,
            total_correct=total_correct,
            total_accuracy=round(total_accuracy, 4) if total_accuracy is not None else None,
            product_count_correct=product_count_correct,
            products_accuracy=round(products_accuracy, 4) if products_accuracy is not None else None
        )

    def _calculate_products_accuracy(
        self, 
        extracted: list, 
        ground_truth: list
    ) -> float:
        """
        Calculate accuracy of product extraction by matching products.
        
        Matches products by name (fuzzy) and checks price accuracy.
        Returns percentage of ground truth products that were correctly extracted.
        """
        if not ground_truth:
            return 1.0 if not extracted else 0.0
        
        matched = 0
        
        for gt_product in ground_truth:
            for ext_product in extracted:
                # Simple name matching (case-insensitive, contains)
                gt_name = gt_product.name.lower().strip()
                ext_name = ext_product.name.lower().strip()
                
                name_match = (
                    gt_name == ext_name or 
                    gt_name in ext_name or 
                    ext_name in gt_name
                )
                
                if name_match:
                    # Check price match (within tolerance)
                    price_match = abs(ext_product.price - gt_product.price) < 0.02
                    if price_match:
                        matched += 1
                        break
        
        return matched / len(ground_truth)

    def _calculate_summary(
        self, run_id: int, model_used: str, results: list[EvaluationResult]
    ) -> EvaluationRunSummary:
        """Calculate summary statistics for an evaluation run."""
        total_files = len(results)
        successful = sum(1 for r in results if r.success)
        failed = total_files - successful
        success_rate = successful / total_files if total_files > 0 else 0.0
        
        # Calculate averages from successful results only
        successful_results = [r for r in results if r.success and r.metrics]
        
        if successful_results:
            avg_processing_time_ms = sum(r.metrics.processing_time_ms for r in successful_results) / len(successful_results)
            avg_field_completeness = sum(r.metrics.field_completeness for r in successful_results) / len(successful_results)
            avg_consistency_rate = sum(1 for r in successful_results if r.metrics.is_consistent) / len(successful_results)
            
            # Ground truth accuracy metrics (only if ground truth comparison was done)
            results_with_gt = [r for r in successful_results if r.metrics.vendor_correct is not None]
            if results_with_gt:
                avg_vendor_accuracy = sum(1 for r in results_with_gt if r.metrics.vendor_correct) / len(results_with_gt)
                avg_date_accuracy = sum(1 for r in results_with_gt if r.metrics.date_correct) / len(results_with_gt)
                avg_total_accuracy = sum(r.metrics.total_accuracy for r in results_with_gt if r.metrics.total_accuracy is not None) / len(results_with_gt)
                avg_products_accuracy = sum(r.metrics.products_accuracy for r in results_with_gt if r.metrics.products_accuracy is not None) / len(results_with_gt)
            else:
                avg_vendor_accuracy = None
                avg_date_accuracy = None
                avg_total_accuracy = None
                avg_products_accuracy = None
        else:
            avg_processing_time_ms = 0.0
            avg_field_completeness = 0.0
            avg_consistency_rate = 0.0
            avg_vendor_accuracy = None
            avg_date_accuracy = None
            avg_total_accuracy = None
            avg_products_accuracy = None
        
        return EvaluationRunSummary(
            run_id=run_id,
            model_used=model_used,
            total_files=total_files,
            successful=successful,
            failed=failed,
            success_rate=round(success_rate, 4),
            avg_processing_time_ms=round(avg_processing_time_ms, 2),
            avg_field_completeness=round(avg_field_completeness, 4),
            avg_consistency_rate=round(avg_consistency_rate, 4),
            results=results,
            avg_vendor_accuracy=round(avg_vendor_accuracy, 4) if avg_vendor_accuracy is not None else None,
            avg_date_accuracy=round(avg_date_accuracy, 4) if avg_date_accuracy is not None else None,
            avg_total_accuracy=round(avg_total_accuracy, 4) if avg_total_accuracy is not None else None,
            avg_products_accuracy=round(avg_products_accuracy, 4) if avg_products_accuracy is not None else None
        )

    def _create_empty_summary(self, run_id: int, model_used: str) -> EvaluationRunSummary:
        """Create an empty summary for when no files are found."""
        return EvaluationRunSummary(
            run_id=run_id,
            model_used=model_used,
            total_files=0,
            successful=0,
            failed=0,
            success_rate=0.0,
            avg_processing_time_ms=0.0,
            avg_field_completeness=0.0,
            avg_consistency_rate=0.0,
            results=[]
        )

    def dispose(self):
        pass
