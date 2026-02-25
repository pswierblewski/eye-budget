import datetime
from dataclasses import dataclass


@dataclass
class Transaction:
    account: int = 0
    date: str = datetime.datetime.now().strftime("%Y-%m-%d")
    status: int = 0
    payee: int = 0
    original_payee: str = ""
    category: int = 0
    memo: str = ""
    number: str = ""
    transfer: int = -1
    fitid: str = ""
    flags: int = 0
    amount: float = 0
    sales_tax: float = 0
    transfer_split: int = -1


@dataclass
class Split:
    transaction: int = 0
    category: int = 0
    payee: int = -1
    amount: float = 0
    transfer: int = -1
    memo: str = ""
    flags: int = 0
