"""Shared helpers for Celery task unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.celery_app import celery_app
from tests.unit.conftest import make_app

TASK_ID = "test-celery-task-id"


@pytest.fixture(autouse=True)
def _celery_memory_result_backend():
    """Task.apply() still records results; default redis backend may be unavailable in venv."""
    prev = celery_app.conf.result_backend
    celery_app.conf.result_backend = "cache+memory://"
    yield
    celery_app.conf.result_backend = prev


def triggers_with_event(mock_pusher: MagicMock, channel: str, event: str) -> list[tuple]:
    """Return list of (args, kwargs) for trigger calls matching channel + event name."""
    matches = []
    for call in mock_pusher.trigger.call_args_list:
        args, kwargs = call
        if len(args) >= 2 and args[0] == channel and args[1] == event:
            matches.append((args, kwargs))
    return matches


def assert_app_disposed(app) -> None:
    """App.dispose() is real code; eye_budget_db_context is always a MagicMock from make_app()."""
    app.eye_budget_db_context.dispose.assert_called_once()
