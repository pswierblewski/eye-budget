"""Derive top LLM category candidate from bank_transactions.category_candidates JSON."""
from __future__ import annotations

import json
from typing import Any


def top_category_candidate_from_stored_json(value: Any) -> dict[str, Any] | None:
    """
    Parse stored JSON and return the candidate with highest category_score.
    Equal scores break ties by lower category_id (stable, deterministic).
    Returns a dict with keys category_id (int), category_name (str), category_score (float), or None.
    """
    if value is None:
        return None
    data = value
    if isinstance(value, (bytes, str)):
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        try:
            data = json.loads(value)
        except json.JSONDecodeError:
            return None
    if not isinstance(data, list) or len(data) == 0:
        return None
    best: dict[str, Any] | None = None
    best_score: float | None = None
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            cid = int(item["category_id"])
            name = str(item.get("category_name", ""))
            score = float(item.get("category_score", 0.0))
        except (KeyError, TypeError, ValueError):
            continue
        if (
            best is None
            or best_score is None
            or score > best_score
            or (score == best_score and cid < int(best["category_id"]))
        ):
            best = {"category_id": cid, "category_name": name, "category_score": score}
            best_score = score
    return best
