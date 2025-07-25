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