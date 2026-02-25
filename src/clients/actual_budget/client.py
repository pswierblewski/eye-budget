from src.clients.base import BudgetClient
from src.data import TransactionModel


class ActualBudgetClient(BudgetClient):
    """
    Actual Budget client stub.
    Implement submit_transaction using the Actual Budget API
    (https://actualbudget.org/docs/api/) when ready.
    """

    def get_name(self) -> str:
        return "actual_budget"

    def submit_transaction(self, transaction_model: TransactionModel) -> str:
        raise NotImplementedError("ActualBudgetClient.submit_transaction is not yet implemented.")

    def dispose(self) -> None:
        print("ActualBudgetClient disposed.")
