from src.clients.my_money.models import Split, Transaction
from src.clients.my_money.db_context import MyMoneyDbContext
from src.data import TransactionModel


class MyMoneyRepository:
    def __init__(self, db_context: MyMoneyDbContext):
        self.db_context = db_context
        self.split_category_id = 1
        self.account_id = 0
        self.to_set_category_id = 143

    def insert_transaction(self, transaction_model: TransactionModel) -> int:
        payee_id = self.db_context.get_payee_by_name(transaction_model.vendor)
        if payee_id is None:
            payee_id = self.db_context.insert_payee(transaction_model.vendor)

        transaction = Transaction(
            account=self.account_id,
            date=transaction_model.date,
            payee=payee_id,
            category=self.split_category_id,
            amount=transaction_model.total * -1,
        )
        transaction_id = self.db_context.insert_transaction(transaction)
        for product in transaction_model.products:
            split = Split(
                transaction=transaction_id,
                category=self.to_set_category_id,
                amount=product.price * -1,
                memo=product.name,
            )
            self.db_context.insert_split(split)
        return transaction_id

    def mark_attachment(self, transaction_id: int):
        self.db_context.update_transaction_flags(transaction_id, 4)
