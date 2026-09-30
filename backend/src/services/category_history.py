from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoryVerdict:
    category_id: int
    category_name: str
    count: int
    share: float


def dominant_category(
    counts: dict[int, tuple[str, int]],
    min_count: int,
    min_share: float,
) -> HistoryVerdict | None:
    total = sum(count for _, count in counts.values())
    if total == 0:
        return None
    category_id, (category_name, count) = max(counts.items(), key=lambda kv: kv[1][1])
    share = count / total
    if count < min_count or share < min_share:
        return None
    return HistoryVerdict(category_id, category_name, count, share)
