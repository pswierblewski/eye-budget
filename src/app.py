from abc import ABC
import os
import time

from src.db_contexts.my_money import MyMoneyDbContext
from src.services.preprocessing import PreprocessingService
from .repositories.files import FilesRepository
from .services.ocr import OCRService
from .repositories.receipts_scans import ReceiptsScansRepository
from .repositories.evaluations import EvaluationsRepository
from .data import (
    ReceiptsScanStatus,
    TransactionModel,
    EvaluationMetrics,
    EvaluationResult,
    EvaluationRunSummary,
)
from .db_contexts.eye_budget import EyeBudgetDbContext
from .repositories.my_money import MyMoneyRepository


class App(ABC):
    def __init__(self):
        self.eye_budget_db_context = EyeBudgetDbContext()
        self.my_money_db_context = MyMoneyDbContext()
        self.files_repository = FilesRepository()
        self.receipts_scans_repository = ReceiptsScansRepository(self.eye_budget_db_context)
        self.evaluations_repository = EvaluationsRepository(self.eye_budget_db_context)
        self.ocr_service = OCRService()
        self.my_money_repository = MyMoneyRepository(self.my_money_db_context)
        self.preprocessing_service = PreprocessingService()

    def run(self, evaluate: bool = False) -> EvaluationRunSummary | None:
        """
        Run the receipt processing pipeline.
        
        Args:
            evaluate: If True, use evaluate/ directory and store metrics without
                     affecting production database. Returns EvaluationRunSummary.
        
        Returns:
            EvaluationRunSummary if evaluate=True, None otherwise.
        """
        if evaluate:
            return self._run_evaluation()
        else:
            self._run_production()
            return None

    def _run_production(self):
        """Run the standard production processing pipeline."""
        files = self.files_repository.list_input_files()
        if not files:
            print("No files to process.")
            return
        for file in files:
            added = self.receipts_scans_repository.add_receipt(file)
            if not added:
                print(f"File {file} already added.")
                continue
            try:
                print(f"Processing file: {file}")
                self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.PROCESSING)
                preprocessed_image_path = self.preprocessing_service.preprocess_image(file)
                ocr_result = self.ocr_service.process_image(preprocessed_image_path)
                self.receipts_scans_repository.set_result(file, ocr_result)
                print(f"File {file} processed successfully.")
                self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.PROCESSED)
                transaction_model = TransactionModel(**ocr_result)
                transaction_id = self.my_money_repository.insert_transaction(transaction_model)
                self.my_money_repository.transaction_has_attachment(transaction_id)
                self.files_repository.move_to_attachment_dir(
                    preprocessed_image_path,
                    f'{transaction_id}.{os.getenv("PREPROCESSED_IMAGE_EXTENSION")}'
                )
            except Exception as e:
                print(f"Error processing file {file}: {e}")
                self.receipts_scans_repository.set_status(file, ReceiptsScanStatus.FAILED, e)

    def _run_evaluation(self) -> EvaluationRunSummary:
        """Run evaluation mode: process files from evaluate/ directory and collect metrics."""
        evaluate_dir = os.getenv("EVALUATE_DIR", "evaluate/")
        model_used = self.ocr_service.model
        
        # Create evaluation run
        run_id = self.evaluations_repository.create_run(
            model_used=model_used,
            config={"evaluate_dir": evaluate_dir}
        )
        
        # List files from evaluate directory
        files = self._list_evaluate_files(evaluate_dir)
        if not files:
            print("No files to evaluate.")
            return self._create_empty_summary(run_id, model_used)
        
        results: list[EvaluationResult] = []
        
        for file in files:
            file_path = os.path.join(evaluate_dir, file)
            result = self._evaluate_single_file(file, file_path)
            results.append(result)
            
            # Store result in database
            self.evaluations_repository.add_result(run_id, result)
        
        # Calculate summary statistics
        summary = self._calculate_summary(run_id, model_used, results)
        
        # Update run with summary
        self.evaluations_repository.update_run_summary(run_id, summary)
        
        return summary

    def _list_evaluate_files(self, evaluate_dir: str) -> list[str]:
        """List files in the evaluate directory."""
        if not os.path.exists(evaluate_dir):
            print(f"Evaluate directory '{evaluate_dir}' does not exist.")
            return []
        return [f for f in os.listdir(evaluate_dir) if os.path.isfile(os.path.join(evaluate_dir, f))]

    def _evaluate_single_file(self, filename: str, file_path: str) -> EvaluationResult:
        """Process a single file and return evaluation result with metrics."""
        start_time = time.time()
        
        try:
            print(f"Evaluating file: {filename}")
            preprocessed_image_path = self.preprocessing_service.preprocess_image(file_path)
            ocr_result = self.ocr_service.process_image(preprocessed_image_path)
            transaction = TransactionModel(**ocr_result)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            metrics = self._calculate_metrics(transaction, processing_time_ms)
            
            print(f"File {filename} evaluated successfully.")
            return EvaluationResult(
                filename=filename,
                success=True,
                metrics=metrics,
                transaction=transaction
            )
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            print(f"Error evaluating file {filename}: {e}")
            return EvaluationResult(
                filename=filename,
                success=False,
                error_message=str(e)
            )

    def _calculate_metrics(self, transaction: TransactionModel, processing_time_ms: int) -> EvaluationMetrics:
        """Calculate evaluation metrics for a transaction."""
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
            is_consistent=is_consistent
        )

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
        else:
            avg_processing_time_ms = 0.0
            avg_field_completeness = 0.0
            avg_consistency_rate = 0.0
        
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
            results=results
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
        self.files_repository.dispose()
        self.receipts_scans_repository.dispose()
        self.evaluations_repository.dispose()
        self.ocr_service.dispose()
        self.my_money_repository.dispose()
        self.my_money_db_context.dispose()
        self.eye_budget_db_context.dispose()
        print("All resources disposed.")
