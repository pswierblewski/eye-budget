import os

from src.clients.base import BudgetClient
from src.clients.my_money.client import MyMoneyClient
from src.clients.actual_budget.client import ActualBudgetClient
from src.clients.firefly_iii.client import FireflyIIIClient


def get_budget_clients() -> list[BudgetClient]:
    """
    Returns a list of all configured budget clients.
    A client is active when its required environment variables are present.
    Add new clients here as they are implemented.
    """
    clients: list[BudgetClient] = []

    if os.getenv("MY_MONEY_SQLITE_PATH"):
        clients.append(MyMoneyClient())

    if os.getenv("ACTUAL_BUDGET_URL"):
        clients.append(ActualBudgetClient())

    if os.getenv("FIREFLY_III_URL"):
        clients.append(FireflyIIIClient())

    return clients
