from src.clients.base import BudgetClient
from src.data import TransactionModel


class FireflyIIIClient(BudgetClient):
    """
    Firefly III client stub.
    Implement submit_transaction using the Firefly III REST API
    (https://docs.firefly-iii.org/references/firefly-iii/api/) when ready.
    Requires env vars: FIREFLY_III_URL, FIREFLY_III_TOKEN.
    """

    def get_name(self) -> str:
        return "firefly_iii"

    def submit_transaction(self, transaction_model: TransactionModel) -> str:
        raise NotImplementedError("FireflyIIIClient.submit_transaction is not yet implemented.")

    def dispose(self) -> None:
        print("FireflyIIIClient disposed.")
