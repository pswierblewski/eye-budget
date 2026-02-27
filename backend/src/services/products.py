from abc import ABC
import json
import os
from openai import OpenAI
from typing import List

from ..data import ProductItem, ProductMappings


class ProductsService(ABC):
    def __init__(self):
        self.client = OpenAI()
        self.model = os.getenv("MODEL", "gpt-5.2")
        self.prompt = (
            "Analyze the following list of Polish product names from a receipt. "
            "For each product name, provide a normalized, human-friendly name in Polish. "
            "Examples:\n"
            "- 'COLGATE ADV WH CHAR75ML A' -> 'Pasta do zębów'\n"
            "- 'PAPIER TOAL.4WAR10X200L A' -> 'Papier toaletowy'\n"
            "- 'MLEKO ŁACIĄTE 2% 1L C' -> 'Mleko'\n"
            "- 'BANANY - KG C' -> 'Banany'\n"
            "- 'OPUST MALINY 125G C' -> 'Rabat maliny'\n"
            "- 'REKLAMÓWKA T-SHIRT A' -> 'Reklamówka'\n"
            "\n"
            "Keep the normalized names simple and generic (remove brands, weights, volumes unless essential). "
            "Return all product mappings."
        )

    def dispose(self):
        """
        Dispose of the service resources.
        """
        print("ProductsService disposed.")

    def process_products(self, products: List[ProductItem]) -> ProductMappings:
        """
        Process a list of products and return normalized product names using OpenAI API.
        
        Args:
            products: List of ProductItem objects from the receipt
            
        Returns:
            ProductMappings object containing the original and normalized product names
        """
        # Extract product names from the products list
        product_names = [product.name for product in products]
        
        # Create the product list text for the prompt
        products_text = "\n".join([f"- {name}" for name in product_names])
        
        full_prompt = f"{self.prompt}\n\nProduct names:\n{products_text}"
        
        tool_name = "normalize_product_names"
        tools = [
            {
                "type": "function",
                "name": tool_name,
                "description": "Normalize Polish product names from receipts to human-friendly names",
                "parameters": ProductMappings.model_json_schema(),
            }
        ]
        
        response = self.client.responses.create(
            model=self.model,
            reasoning={"effort": "medium"},
            tools=tools,
            tool_choice={"type": "function", "name": tool_name},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": full_prompt}
                    ],
                }
            ],
        )
        
        tool_call = next(
            (item for item in response.output if item.type == "function_call"),
            None,
        )
        if tool_call is None:
            raise ValueError("No function call found in OpenAI response")
        response_arguments = tool_call.arguments
        args = json.loads(response_arguments)
        
        return ProductMappings(**args)