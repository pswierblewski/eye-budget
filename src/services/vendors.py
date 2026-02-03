from abc import ABC
import json
import os
from openai import OpenAI

from ..data import VendorMapping


class VendorsService(ABC):
    def __init__(self):
        self.client = OpenAI()
        self.model = os.getenv("MODEL", "gpt-5.2")
        self.prompt = (
            "Analyze the following Polish vendor/store name from a receipt. "
            "Provide a normalized, human-friendly vendor name in Polish. "
            "Remove legal entity suffixes like 'Sp. z o.o.', 'S.A.', 'sp. j.', etc. "
            "Keep the name simple and recognizable.\n"
            "\n"
            "Examples:\n"
            "- 'ALDI Sp. z o.o.' -> 'Aldi'\n"
            "- 'BIEDRONKA S.A.' -> 'Biedronka'\n"
            "- 'KAUFLAND POLSKA MARKETY SP. Z O.O.' -> 'Kaufland'\n"
            "- 'LIDL POLSKA SP. Z O.O.' -> 'Lidl'\n"
            "- 'LEROY MERLIN POLSKA SP Z O O' -> 'Leroy Merlin'\n"
            "- 'ZABKA POLSKA SP. Z O.O.' -> 'Żabka'\n"
            "- 'CARREFOUR POLSKA SP. Z O.O.' -> 'Carrefour'\n"
            "\n"
            "Return the normalized vendor name."
        )

    def dispose(self):
        """
        Dispose of the service resources.
        """
        print("VendorsService disposed.")

    def process_vendor(self, vendor_name: str) -> VendorMapping:
        """
        Process a vendor name and return a normalized vendor name using OpenAI API.
        
        Args:
            vendor_name: The vendor name as it appears on the receipt
            
        Returns:
            VendorMapping object containing the original and normalized vendor name
        """
        full_prompt = f"{self.prompt}\n\nVendor name from receipt:\n{vendor_name}"
        
        tool_name = "normalize_vendor_name"
        tools = [
            {
                "type": "function",
                "name": tool_name,
                "description": "Normalize Polish vendor/store name from receipt to human-friendly name",
                "parameters": VendorMapping.model_json_schema(),
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
        
        response_arguments = response.output[0].arguments
        args = json.loads(response_arguments)
        
        return VendorMapping(**args)

