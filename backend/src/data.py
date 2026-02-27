import datetime
from enum import StrEnum
from pydantic import BaseModel, Field
from typing import List, Optional

class ReceiptsScanStatus(StrEnum):
    """Enumeration for the status of a receipt scan"""
    NEW = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed",
    TO_CONFIRM = "to_confirm",
    DONE = "done"


class ProductItem(BaseModel):
    """Represents a purchased product"""
    name: str = Field(..., description="The name of the product.")
    quantity: float = Field(..., description="The quantity of the product purchased.")
    price: float = Field(..., description="The price of the product.")
    unit_price: float | None = Field(
        default=None,
        description="The price for quantity=1 of the product"
    )


class TransactionModel(BaseModel):
    """Represents a complete purchase transaction"""
    vendor: str = Field(..., description="The name of the store where the purchase was made.")
    title: str = Field(..., description="The title of the document, typically 'PARAGON FISKALNY'.")
    products: List[ProductItem] = Field(
        ..., 
        description="A list of products purchased, including name, quantity, and price for each item. Discounts, rabates, bonuses and other product-related discounts are represented as products with negative prices."
    )
    total: float = Field(..., description="The total amount to be paid for the transaction.")
    date: str = Field(..., description="The date when the transaction occurred.")


class CategoryCandidate(BaseModel):
    """Represents category candidate for a single product"""
    category_id: int = Field(..., description="The unique identifier for the category candidate.")
    category_name: str = Field(..., description="The name of the category candidate.")
    category_score: float = Field(..., description="The confidence score for the category match.")


class CategoryCandidates(BaseModel):
    """Represents category candidates for a transaction"""
    category_candidates: List[CategoryCandidate] = Field(
        ...,
        description="A list of category candidates for each product in the transaction."
    )
    product_name: str = Field(..., description="The name of the product for which the category candidate is suggested.")
    

class CategoryCandidatesProducts(BaseModel):
    """Represents category candidates for multiple products in a transaction"""
    category_candidates: List[CategoryCandidates] = Field(
        ...,
        description="A list of category candidates for each product in the transaction."
    )


class ProductMapping(BaseModel):
    """Represents a mapping between receipt product name and normalized product name"""
    product_alternative_name: str = Field(..., description="The original product name as it appears on the receipt.")
    product_name: str = Field(..., description="The normalized, human-friendly product name (e.g., 'Pasta do zębów' for 'COLGATE ADV WH CHAR75ML A').")


class ProductMappings(BaseModel):
    """Represents a list of product mappings"""
    products: List[ProductMapping] = Field(
        ...,
        description="A list of product mappings with original and normalized names."
    )

class VendorItem(BaseModel):
    """Represents a vendor in the database"""
    id: int = Field(..., description="The unique identifier for the vendor.")
    name: str = Field(..., description="The normalized vendor name.")

class NormalizedProductItem(BaseModel):
    """Represents a normalized product in the database"""
    id: int = Field(..., description="The unique identifier for the product.")
    name: str = Field(..., description="The normalized product name.")

class VendorMapping(BaseModel):
    """Represents a mapping between receipt vendor name and normalized vendor name"""
    vendor_alternative_name: str = Field(..., description="The original vendor name as it appears on the receipt.")
    vendor_name: str = Field(..., description="The normalized, human-friendly vendor name (e.g., 'Aldi' for 'ALDI Sp. z o.o.').")


class EvaluationMetrics(BaseModel):
    """Metrics for a single receipt evaluation"""
    processing_time_ms: int = Field(..., description="Time to process the receipt in milliseconds.")
    fields_extracted: int = Field(..., description="Count of non-null fields extracted.")
    field_completeness: float = Field(..., description="Ratio of extracted fields to total expected fields.")
    product_count: int = Field(..., description="Number of products extracted.")
    has_vendor: bool = Field(..., description="Whether vendor was extracted.")
    has_date: bool = Field(..., description="Whether date was extracted.")
    has_total: bool = Field(..., description="Whether total was extracted.")
    products_sum: float = Field(..., description="Sum of all product prices.")
    extracted_total: float = Field(..., description="Total amount as extracted from receipt.")
    total_difference: float = Field(..., description="Absolute difference between products_sum and extracted_total.")
    is_consistent: bool = Field(..., description="Whether products_sum matches extracted_total within tolerance.")
    # Ground truth comparison metrics (optional, only present when comparing against ground truth)
    vendor_correct: Optional[bool] = Field(default=None, description="Whether extracted vendor matches ground truth.")
    date_correct: Optional[bool] = Field(default=None, description="Whether extracted date matches ground truth.")
    total_correct: Optional[bool] = Field(default=None, description="Whether extracted total is within tolerance of ground truth.")
    total_accuracy: Optional[float] = Field(default=None, description="Accuracy of total: 1.0 - (abs(extracted - expected) / expected).")
    product_count_correct: Optional[bool] = Field(default=None, description="Whether product count matches ground truth.")
    products_accuracy: Optional[float] = Field(default=None, description="Percentage of products matched correctly.")


class EvaluationResult(BaseModel):
    """Result of evaluating a single receipt"""
    filename: str = Field(..., description="Name of the processed file.")
    success: bool = Field(..., description="Whether processing completed without error.")
    error_message: str | None = Field(default=None, description="Error details if processing failed.")
    metrics: EvaluationMetrics | None = Field(default=None, description="Evaluation metrics if successful.")
    transaction: TransactionModel | None = Field(default=None, description="Extracted transaction data if successful.")


class EvaluationRunSummary(BaseModel):
    """Summary of an evaluation run"""
    run_id: int = Field(..., description="Unique identifier for this evaluation run.")
    model_used: str = Field(..., description="Model identifier used for processing.")
    total_files: int = Field(..., description="Total number of files processed.")
    successful: int = Field(..., description="Number of successfully processed files.")
    failed: int = Field(..., description="Number of failed files.")
    success_rate: float = Field(..., description="Ratio of successful to total files.")
    avg_processing_time_ms: float = Field(..., description="Average processing time per file.")
    avg_field_completeness: float = Field(..., description="Average field completeness across all files.")
    avg_consistency_rate: float = Field(..., description="Percentage of files with consistent totals.")
    results: List[EvaluationResult] = Field(..., description="Individual results for each file.")
    # Ground truth comparison metrics (optional, only present when comparing against ground truth)
    avg_vendor_accuracy: Optional[float] = Field(default=None, description="Percentage of correct vendor extractions.")
    avg_date_accuracy: Optional[float] = Field(default=None, description="Percentage of correct date extractions.")
    avg_total_accuracy: Optional[float] = Field(default=None, description="Average total accuracy across all files.")
    avg_products_accuracy: Optional[float] = Field(default=None, description="Average products accuracy across all files.")


class GroundTruthEntry(BaseModel):
    """Internal model for database operations - represents a ground truth record"""
    id: int = Field(..., description="Unique identifier for this ground truth entry.")
    filename: str = Field(..., description="Original filename of the receipt image.")
    minio_object_key: str = Field(..., description="MinIO object key where the image is stored.")
    ground_truth: TransactionModel = Field(..., description="The verified/corrected transaction data.")
    created_at: datetime.datetime = Field(..., description="When this entry was created.")
    updated_at: datetime.datetime = Field(..., description="When this entry was last updated.")


class GroundTruthResponse(BaseModel):
    """API response model for ground truth operations"""
    id: int = Field(..., description="Unique identifier for this ground truth entry.")
    filename: str = Field(..., description="Original filename of the receipt image.")
    ground_truth: TransactionModel = Field(..., description="The verified/corrected transaction data.")
    created_at: datetime.datetime = Field(..., description="When this entry was created.")


# ---------------------------------------------------------------------------
# Receipt review / confirm models
# ---------------------------------------------------------------------------

class ReceiptScanListItem(BaseModel):
    """Lightweight scan summary for list views."""
    id: int
    filename: str
    status: str
    vendor: str | None = None
    date: str | None = None
    total: float | None = None


class ReceiptTransactionItem(BaseModel):
    """A single line item in a confirmed receipt transaction."""
    id: int
    product_id: int | None = None
    raw_product_name: str
    normalized_product_name: str | None = None
    category_id: int
    quantity: float
    unit_price: float | None = None
    price: float


class ReceiptTransaction(BaseModel):
    """A confirmed receipt transaction with all its line items."""
    id: int
    vendor_id: int | None = None
    raw_vendor_name: str
    normalized_vendor_name: str | None = None
    date: str
    total: float
    items: list[ReceiptTransactionItem]


class ReceiptScanDetail(BaseModel):
    """Full scan detail including OCR result and confirmed transaction if available."""
    id: int
    filename: str
    status: str
    result: TransactionModel | None = None
    categories_candidates: dict | None = None
    minio_object_key: str | None = None
    transaction: ReceiptTransaction | None = None  # populated once confirmed
    # Pre-fill suggestions: normalized names already known from DB for the raw OCR names
    vendor_normalization: str | None = None
    product_normalizations: dict[str, str | None] | None = None


class CategoryItem(BaseModel):
    """A single expense category with parent and group context."""
    id: int
    name: str
    parent_name: str | None = None
    group_name: str | None = None


class ConfirmReceiptRequest(BaseModel):
    """Request body for confirming a receipt: maps raw product names to category IDs.

    Optional fields allow overriding OCR-sourced values before the transaction is created.
    """
    product_categories: dict[str, int]  # {raw_product_name: category_id}
    # Optional overrides for OCR-sourced fields
    vendor: str | None = None
    date: str | None = None
    total: float | None = None
    products: List[ProductItem] | None = None
    # Optional normalized name overrides — if provided they are looked up (or created) in the
    # vendors/products tables and linked as alternative names for the raw receipt names.
    normalized_vendor: str | None = None
    normalized_products: dict[str, str] | None = None  # {raw_product_name: normalized_name}


# ---------------------------------------------------------------------------
# Evaluation list/detail models (lighter than EvaluationRunSummary)
# ---------------------------------------------------------------------------

class EvaluationRunListItem(BaseModel):
    """Summary row for the evaluations list view."""
    id: int
    run_timestamp: datetime.datetime
    model_used: str
    total_files: int
    successful: int
    failed: int
    success_rate: float | None = None
    avg_processing_time_ms: float | None = None
    avg_field_completeness: float | None = None
    avg_consistency_rate: float | None = None
    config: dict | None = None


class EvaluationRunDetail(EvaluationRunListItem):
    """Full evaluation run including per-file results."""
    results: list[EvaluationResult]