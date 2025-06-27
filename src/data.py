from pydantic import BaseModel, Field
from typing import List

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
        description="A list of products purchased, including name, quantity, and price for each item."
    )
    total: float = Field(..., description="The total amount to be paid for the transaction.")
    date: str = Field(..., description="The date when the transaction occurred.")
