from abc import ABC
import json

from openai import OpenAI

from ..repositories.categories import CategoriesRepository
from ..services.markdown_table import MarkdownTableService
from ..data import TransactionModel, CategoryCandidatesProducts


class CategoriesService(ABC):
    def __init__(self, db_context):
        self.categories_repository = CategoriesRepository(db_context=db_context)
        self.markdown_table_service = MarkdownTableService()
        self.client = OpenAI()
        self.model = "gpt-4.1"
        self.categories = ""
        self.prompt = """
You are an expert in Polish fiscal receipts.
Your task is to assign category candidates to every product in the transaction.
Below is a list of available categories.
================
{0}
================
And below is the transaction data:
================
{1}
Please analyze the transaction and return category_ids with a name and a confidence score of the most appropriate category candidates to each product.
        """

    def build(self):
        self.categories = self._get_categories()

    def _get_categories(self) -> str:
        categories = self.categories_repository.get_categories()
        mapped = self._map_categories(categories)
        return mapped

    def _map_categories(self, categories: list) -> str:
        ids = ['category_id']
        category_names = ['category_name']
        parent_names = ['category_parent_name']
        category_groups = ['category_group_name']
        for category in categories:
            ids.append(category[0])
            category_names.append(category[1])
            parent_names.append(category[2])
            category_groups.append(category[3])
        table = self.markdown_table_service.table(
            [ids, category_names, parent_names, category_groups]
        )
        return table

    def assign_category_candidates(self, transaction_model: TransactionModel):
        tool_name = "get_category_candidates"
        tools = [
            {
                "type": "function",
                "name": tool_name,
                "description": "Get category candidates for each product in the transaction",
                "parameters": CategoryCandidatesProducts.model_json_schema(),
            }
        ]
        prompt = self.prompt.format(
            self.categories,
            transaction_model.model_dump_json(),
        )
        response = self.client.responses.create(
            model=self.model,
            temperature=0.0,
            tools=tools,
            tool_choice={"type": "function", "name": tool_name},
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                    ],
                }
            ],
        )
        response_arguments = response.output[0].arguments
        args = json.loads(response_arguments)
        return args
