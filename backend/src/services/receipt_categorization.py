from __future__ import annotations

from dataclasses import dataclass

from ..data import TransactionModel
from .category_history import dominant_category
from .receipt_auto_confirm import (
    SOURCE_AI,
    SOURCE_HISTORY,
    AutoConfirmSettings,
    ProductResolution,
    normalize_score,
)

MAX_EXAMPLES = 30
EXAMPLES_PER_PRODUCT = 5


@dataclass(frozen=True)
class CategorizationResult:
    candidates: dict
    resolutions: list[ProductResolution]
    vendor_has_history: bool


class ReceiptCategorizationService:
    def __init__(self, product_resolver, categories_service, category_history_repository, settings: AutoConfirmSettings):
        self.product_resolver = product_resolver
        self.categories_service = categories_service
        self.category_history_repository = category_history_repository
        self.settings = settings

    def categorize(self, transaction_model: TransactionModel, vendor_id: int | None) -> CategorizationResult:
        raw_names = [p.name for p in transaction_model.products]
        unique_names = list(dict.fromkeys(raw_names))
        by_name = {r.raw_name: r for r in self.product_resolver.resolve(raw_names)}

        product_ids = sorted({r.product_id for r in by_name.values() if r.product_id is not None})
        counts = self.category_history_repository.get_category_counts(product_ids)
        verdicts = {}
        for name, resolved in by_name.items():
            if resolved.product_id is None:
                continue
            verdict = dominant_category(
                counts.get(resolved.product_id, {}),
                self.settings.history_min_count,
                self.settings.history_min_share,
            )
            if verdict is not None:
                verdicts[name] = verdict

        ai_by_name: dict[str, list[dict]] = {}
        needs_ai = [n for n in unique_names if n not in verdicts]
        if needs_ai:
            subset = transaction_model.model_copy(
                update={"products": [p for p in transaction_model.products if p.name in set(needs_ai)]}
            )
            response = self.categories_service.assign_category_candidates(
                subset, examples=self._examples(needs_ai, by_name)
            )
            valid_ids = self.categories_service.category_ids
            for entry in (response or {}).get("category_candidates", []):
                candidates = [
                    c for c in entry.get("category_candidates", [])
                    if not valid_ids or c.get("category_id") in valid_ids
                ]
                ai_by_name[entry.get("product_name", "")] = candidates

        entries: list[dict] = []
        resolutions: list[ProductResolution] = []
        for name in unique_names:
            resolved = by_name[name]
            verdict = verdicts.get(name)
            if verdict is not None:
                entries.append({
                    "product_name": name,
                    "category_candidates": [{
                        "category_id": verdict.category_id,
                        "category_name": verdict.category_name,
                        "category_score": round(verdict.share, 4),
                    }],
                    "source": SOURCE_HISTORY,
                    "product_id": resolved.product_id,
                    "history_count": verdict.count,
                })
                resolutions.append(
                    ProductResolution(
                        name,
                        resolved.product_id,
                        resolved.normalized_name,
                        verdict.category_id,
                        verdict.category_name,
                        SOURCE_HISTORY,
                        verdict.share,
                        verdict.count,
                    )
                )
                continue
            candidates = ai_by_name.get(name, [])
            top = max(candidates, key=lambda c: c.get("category_score", 0), default=None)
            entries.append({
                "product_name": name,
                "category_candidates": candidates,
                "source": SOURCE_AI,
                "product_id": resolved.product_id,
                "history_count": 0,
            })
            resolutions.append(
                ProductResolution(
                    name,
                    resolved.product_id,
                    resolved.normalized_name,
                    top.get("category_id") if top else None,
                    top.get("category_name") if top else None,
                    SOURCE_AI,
                    normalize_score(float(top.get("category_score", 0))) if top else 0.0,
                    0,
                )
            )

        return CategorizationResult(
            candidates={"category_candidates": entries},
            resolutions=resolutions,
            vendor_has_history=self.category_history_repository.vendor_has_confirmed_receipts(vendor_id),
        )

    def _examples(self, names: list[str], by_name: dict) -> list[tuple[str, str]]:
        similar_ids: dict[str, int] = {}
        for name in names:
            similar = by_name[name].similar or self.product_resolver.find_similar(name)
            for s in similar[:EXAMPLES_PER_PRODUCT]:
                similar_ids.setdefault(s.name, s.product_id)
        if not similar_ids:
            return []
        counts = self.category_history_repository.get_category_counts(sorted(set(similar_ids.values())))
        examples = []
        for alt_name, product_id in similar_ids.items():
            verdict = dominant_category(counts.get(product_id, {}), min_count=1, min_share=0.5)
            if verdict is not None:
                examples.append((alt_name, verdict.category_name))
        return examples[:MAX_EXAMPLES]
