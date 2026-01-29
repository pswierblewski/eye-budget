from dataclasses import dataclass
import datetime
from enum import StrEnum
from pydantic import BaseModel, Field
from typing import List

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


@dataclass
class Transaction():
    account: int = 0
    date: str = datetime.datetime.now().strftime("%Y-%m-%d")
    status: int = 0
    payee: int = 0
    original_payee: str = ""
    category: int = 0
    memo: str = ""
    number: str = ""
    transfer: int = -1
    fitid: str = ""
    flags: int = 0
    amount: float = 0
    sales_tax: float = 0
    transfer_split: int = -1


@dataclass
class Split():
    transaction: int = 0
    category: int = 0
    payee: int = -1
    amount: float = 0
    transfer: int = -1
    memo: str = ""
    flags: int = 0


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