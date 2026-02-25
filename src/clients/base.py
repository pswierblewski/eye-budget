from abc import ABC, abstractmethod

from src.data import TransactionModel


class BudgetClient(ABC):
    @abstractmethod
    def get_name(self) -> str:
        """Returns unique client identifier used in client_syncs tracking."""
        ...

    @abstractmethod
    def submit_transaction(self, transaction_model: TransactionModel) -> str:
        """
        Submits a transaction to the client's database.
        Returns external_id (string) stored in client_syncs for reference.
        """
        ...

    def attach_file(self, external_id: str, file_path: str) -> None:
        """
        Optionally attaches a file to the submitted transaction.
        Default implementation is a no-op; override in clients that support attachments.
        """
        pass

    @abstractmethod
    def dispose(self) -> None: ...
