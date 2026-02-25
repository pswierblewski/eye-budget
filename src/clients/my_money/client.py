import os
import shutil

from src.clients.base import BudgetClient
from src.clients.my_money.db_context import MyMoneyDbContext
from src.clients.my_money.repository import MyMoneyRepository
from src.data import TransactionModel


class MyMoneyClient(BudgetClient):
    def __init__(self):
        self._db_context = MyMoneyDbContext()
        self._repository = MyMoneyRepository(self._db_context)

    def get_name(self) -> str:
        return "my_money"

    def submit_transaction(self, transaction_model: TransactionModel) -> str:
        transaction_id = self._repository.insert_transaction(transaction_model)
        self._repository.mark_attachment(transaction_id)
        return str(transaction_id)

    def attach_file(self, external_id: str, file_path: str) -> None:
        attachments_dir = os.getenv("MY_MONEY_ATTACHMENTS_DIR")
        if not attachments_dir:
            return
        extension = os.getenv("PREPROCESSED_IMAGE_EXTENSION", "png")
        dest = os.path.join(attachments_dir, f"{external_id}.{extension}")
        shutil.copy2(file_path, dest)
        print(f"Attachment copied to {dest}.")

    def dispose(self) -> None:
        self._db_context.dispose()
        print("MyMoneyClient disposed.")
