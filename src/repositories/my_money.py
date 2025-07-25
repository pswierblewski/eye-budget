from abc import ABC

from src.data import Split, Transaction, TransactionModel
from src.db_contexts.my_money import MyMoneyDbContext


class MyMoneyRepository(ABC):
    def __init__(self, db_context: MyMoneyDbContext):
        self.my_money_db_context = db_context
        self.split_category_id = 1
        self.account_id = 0
        self.to_set_category_id = 143

    def insert_transaction(self, transaction_model: TransactionModel):
        payee_id = self.my_money_db_context.get_payee_by_name(transaction_model.vendor)
        if payee_id is None:
            payee_id = self.my_money_db_context.insert_payee(transaction_model.vendor)
        
        transaction = Transaction(
            account=self.account_id,
            date=transaction_model.date,
            payee=payee_id,
            category=self.split_category_id,
            amount=transaction_model.total * -1,
        )
        transaction_id = self.my_money_db_context.insert_transaction(transaction)
        for product in transaction_model.products:
            split = Split(
                transaction=transaction_id,
                category=self.to_set_category_id,
                amount=product.price * -1,
                memo=product.name
            )
            self.my_money_db_context.insert_split(split)
        return transaction_id

    def transaction_has_attachment(self, transaction_id: int):
        self.my_money_db_context.update_transaction_flags(transaction_id, 4)

    def dispose(self):
        print("MyMoneyRepository disposed.")

