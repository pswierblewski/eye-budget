from abc import ABC
import base64
import json
import os
import time
from openai import OpenAI
from ..data import TransactionModel
from PIL import Image


class OCRService(ABC):
    def __init__(self):
        self.client = OpenAI()
        self.input_dir = os.getenv("INPUT_DIR", "input/")
        self.output_dir = os.getenv("OUTPUT_DIR", "output/")
        self.prompt = (
            "Analyze this Polish fiscal receipt. Extract: "
            "1. Vendor name. "
            "2. Title (PARAGON FISKALNY). "
            "3. Product list (name, quantity, price, unit_price). "
            "4. Discounts, rabates, bonuses and other product-related discounts should be taken into account as well. Take them into the product list as a product with negative price."
            "5. Total amount. "
            "6. Transaction date (only date without time). "
            "Return only valid data; omit missing fields."
        )
        self.model = "gpt-4.1"
        
    def dispose(self):
        """
        Dispose of the service resources.
        This method is a placeholder for any cleanup operations needed.
        """
        print("OCRService disposed.")

    def _encode_image(self, image_path: str) -> str:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(
                image_file.read()).decode("utf-8")
        return encoded_string

    def process_image(self, image_path: str) -> dict:
        base64_image = self._encode_image(image_path)
        tool_name = "extract_receipt_data"
        tools = [
            {
                "type": "function",
                "name": tool_name,
                "description": "Extract structured data from Polish receipts",
                "parameters": TransactionModel.model_json_schema(),
            }
        ]
        response = self.client.responses.create(
            model=self.model,
            temperature=0.0,
            tools=tools,
            tool_choice={"type": "function", "name": tool_name},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text":
                            self.prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high"
                        },
                    ],
                }
            ],
        )
        response_arguments = response.output[0].arguments
        args = json.loads(response_arguments)
        return args
