from abc import ABC
import asyncio
import base64
import json
import os
import time
from openai import AsyncOpenAI, OpenAI
from ..data import TransactionModel
from PIL import Image


class OCRService(ABC):
    def __init__(self):
        self.client = OpenAI()
        self.async_client = AsyncOpenAI()
        self.prompt = (
            "Analyze this Polish fiscal receipt. Extract: "
            "1. Vendor name. "
            "2. Title (PARAGON FISKALNY). "
            "3. Product list (name, quantity, price, unit_price). "
            "4. Discounts and rebates: "
            "   - Lines like 'Uwzgl. rabat: -X,XX st. c Y,YY' mean a discount was applied to the preceding product. "
            "     'st. c Y,YY' is the original price — use it as that product's price and unit_price. "
            "     Add the discount as a separate product entry with negative price (e.g. name: 'Rabat (Uwzgl. rabat)', price: -X.XX). "
            "   - Lines like 'Rabat <name>' with a negative amount in the right column are standalone discount lines — "
            "     add them as a separate product entry with that negative price. "
            "   - In all cases, discounts and rebates must appear in the product list with a negative price. "
            "5. Total amount. "
            "6. Transaction date (only date without time). Output format: YYYY-MM-DD. "
            "   Receipts use various date formats — always convert to YYYY-MM-DD: "
            "   - 'dn.25r10.30' → 2025-10-30  (dn=dzień day, r=rok year; pattern dn.YYrMM.DD). "
            "   - '2025-10-31' → 2025-10-31  (ISO date, use as-is). "
            "   - '2025-10-30 08:22' → 2025-10-30  (ISO datetime, drop the time part). "
            "   - '28-11-2025' → 2025-11-28  (DD-MM-YYYY). "
            "   - '27-01-2026' → 2026-01-27  (DD-MM-YYYY). "
            "Return only valid data; omit missing fields."
        )
        self.model = os.getenv("MODEL", "gpt-5.2")
        
    def dispose(self):
        pass

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
            reasoning={"effort": "medium"},
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
        tool_call = next(
            (item for item in response.output if item.type == "function_call"),
            None,
        )
        if tool_call is None:
            raise ValueError("No function call found in OpenAI response")
        response_arguments = tool_call.arguments
        args = json.loads(response_arguments)
        return args

    async def process_image_async(self, image_path: str) -> dict:
        """Async version of process_image — uses AsyncOpenAI for concurrent calls."""
        base64_image = await asyncio.to_thread(self._encode_image, image_path)
        tool_name = "extract_receipt_data"
        tools = [
            {
                "type": "function",
                "name": tool_name,
                "description": "Extract structured data from Polish receipts",
                "parameters": TransactionModel.model_json_schema(),
            }
        ]
        response = await self.async_client.responses.create(
            model=self.model,
            reasoning={"effort": "medium"},
            tools=tools,
            tool_choice={"type": "function", "name": tool_name},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": self.prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{base64_image}",
                            "detail": "high",
                        },
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
        return json.loads(tool_call.arguments)
