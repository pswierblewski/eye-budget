import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "unit: pure unit test, no Docker")
    config.addinivalue_line("markers", "integration: requires Docker")
