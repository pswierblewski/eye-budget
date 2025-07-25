import os
import sqlite3
from abc import ABC

from src.data import Split, Transaction


class MyMoneyDbContext(ABC):
    def __init__(self):
        self.conn = None
        self.connect_db()

    def connect_db(self):
        try:
            db_path = os.getenv("MY_MONEY_SQLITE_PATH", "sqlite/mymoney.mmdb")
            self.conn = sqlite3.connect(db_path)
            print(f"SQLite database connection established at {db_path}.")
            return self.conn
        except Exception as e:
            print("Failed to connect to SQLite database:", e)

    def get_max_id_payees(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(Id) FROM Payees")
        result = cursor.fetchone()
        if result[0] is None:
            return -1
        return result[0]

    def get_max_id_transactions(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(Id) FROM Transactions")
        result = cursor.fetchone()
        if result[0] is None:
            return -1
        return result[0]

    def get_max_id_splits(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(Id) FROM Splits")
        result = cursor.fetchone()
        if result[0] is None:
            return -1
        return result[0]

    def get_payee_by_name(self, name):
        cursor = self.conn.cursor()
        cursor.execute("SELECT Id FROM Payees WHERE Name = ?", (name,))
        result = cursor.fetchone()
        if result is None or result[0] is None:
            return None
        return result[0]

    def insert_payee(self, name):
        cursor = self.conn.cursor()
        max_id = self.get_max_id_payees()   
        new_id = max_id + 1
        cursor.execute("INSERT INTO Payees (Id, Name) VALUES (?, ?)", (new_id, name))
        self.conn.commit()
        return new_id

    def insert_transaction(self, transaction: Transaction):
        cursor = self.conn.cursor()
        max_id = self.get_max_id_transactions()
        new_id = max_id + 1
        cursor.execute("INSERT INTO Transactions (Id, Account, Date, Status, Payee, OriginalPayee, Category, Memo, Number, Transfer, FITID, Flags, Amount, SalesTax, TransferSplit) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (new_id, transaction.account, transaction.date, transaction.status, transaction.payee, transaction.original_payee, transaction.category, transaction.memo, transaction.number, transaction.transfer, transaction.fitid, transaction.flags, transaction.amount, transaction.sales_tax, transaction.transfer_split))
        self.conn.commit()
        return new_id

    def insert_split(self, split: Split):
        cursor = self.conn.cursor()
        max_id = self.get_max_id_splits()
        cursor.execute('INSERT INTO Splits ("Transaction", Id, Category, Payee, Amount, Transfer, Memo, Flags) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (split.transaction, max_id + 1, split.category, split.payee, split.amount, split.transfer, split.memo, split.flags))
        self.conn.commit()

    def update_transaction_flags(self, transaction_id: int, flags: int):
        cursor = self.conn.cursor()
        cursor.execute('UPDATE Transactions SET "Flags" = ? WHERE Id = ?', (flags, transaction_id))
        self.conn.commit()

    def dispose(self):
        if self.conn:
            self.conn.close()
            print("SQLite database connection closed.")
        else:
            print("No SQLite database connection to close.")