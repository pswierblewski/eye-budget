from __future__ import annotations

from dataclasses import dataclass, replace

from rapidfuzz import fuzz, process, utils

from ..data import NormalizedProductItem

FUZZY_AUTO_ACCEPT = 0.85
SHORTLIST_SIZE = 10
SHORTLIST_MIN_SIMILARITY = 0.3


@dataclass(frozen=True)
class SimilarName:
    name: str
    product_id: int
    score: float


@dataclass(frozen=True)
class ResolvedProduct:
    raw_name: str
    product_id: int | None
    normalized_name: str | None
    method: str
    similar: list[SimilarName]


class ProductResolver:
    def __init__(self, products_repository, products_service):
        self.products_repository = products_repository
        self.products_service = products_service
        self._trigram: bool | None = None
        self._fallback_names: list[tuple[str, int]] | None = None

    def resolve(self, raw_names: list[str]) -> list[ResolvedProduct]:
        resolved: dict[str, ResolvedProduct] = {}
        pending: list[tuple[str, list[SimilarName]]] = []

        for raw_name in dict.fromkeys(raw_names):
            product_id = self.products_repository.get_product_by_alternative_name(raw_name)
            if product_id is not None:
                resolved[raw_name] = ResolvedProduct(raw_name, product_id, None, "exact", [])
                continue
            similar = self.find_similar(raw_name)
            if similar and similar[0].score >= FUZZY_AUTO_ACCEPT:
                best = similar[0]
                self.products_repository.insert_alternative_name(raw_name, best.product_id)
                resolved[raw_name] = ResolvedProduct(raw_name, best.product_id, None, "fuzzy", similar)
                continue
            pending.append((raw_name, similar))

        if pending:
            resolved.update(self._resolve_with_llm(pending))

        ids = [r.product_id for r in resolved.values() if r.product_id is not None]
        names = self.products_repository.get_names_by_ids(sorted(set(ids)))
        return [
            replace(resolved[n], normalized_name=names.get(resolved[n].product_id, resolved[n].normalized_name))
            for n in raw_names
        ]

    def find_similar(self, raw_name: str) -> list[SimilarName]:
        rows: list[tuple[str, int, float]]
        if self._trigram is None:
            self._trigram = self.products_repository.has_trigram_support()
        if self._trigram:
            try:
                rows = self.products_repository.find_similar_alternative_names(
                    raw_name, limit=SHORTLIST_SIZE, min_similarity=SHORTLIST_MIN_SIMILARITY
                )
            except Exception as e:
                print(f"Trigram search failed, falling back to rapidfuzz: {e}")
                self._trigram = False
                rows = self._fuzzy_rows(raw_name)
        else:
            rows = self._fuzzy_rows(raw_name)
        return [SimilarName(name, pid, float(score)) for name, pid, score in rows if name != raw_name]

    def _fuzzy_rows(self, raw_name: str) -> list[tuple[str, int, float]]:
        if self._fallback_names is None:
            self._fallback_names = self.products_repository.get_all_alternative_names()
        choices = {i: name for i, (name, _) in enumerate(self._fallback_names)}
        matches = process.extract(
            raw_name, choices, scorer=fuzz.ratio, processor=utils.default_process, limit=SHORTLIST_SIZE
        )
        rows = []
        for name, score, index in matches:
            normalized = score / 100.0
            if normalized >= SHORTLIST_MIN_SIMILARITY:
                rows.append((name, self._fallback_names[index][1], normalized))
        return rows

    def _resolve_with_llm(self, pending: list[tuple[str, list[SimilarName]]]) -> dict[str, ResolvedProduct]:
        candidate_ids = sorted({s.product_id for _, similar in pending for s in similar})
        names_by_id = self.products_repository.get_names_by_ids(candidate_ids)

        items: list[tuple[str, list[NormalizedProductItem]]] = []
        allowed: dict[str, set[int]] = {}
        for raw_name, similar in pending:
            candidates: list[NormalizedProductItem] = []
            for s in similar:
                if s.product_id in allowed.setdefault(raw_name, set()) or s.product_id not in names_by_id:
                    continue
                allowed[raw_name].add(s.product_id)
                candidates.append(NormalizedProductItem(id=s.product_id, name=names_by_id[s.product_id]))
            items.append((raw_name, candidates))

        try:
            decisions = {i.raw_name: i for i in self.products_service.resolve_products(items).items}
        except Exception as e:
            print(f"LLM product resolution failed: {e}")
            decisions = {}

        out: dict[str, ResolvedProduct] = {}
        for raw_name, similar in pending:
            decision = decisions.get(raw_name)
            if decision and decision.product_id in allowed.get(raw_name, set()):
                self.products_repository.insert_alternative_name(raw_name, decision.product_id)
                out[raw_name] = ResolvedProduct(raw_name, decision.product_id, None, "llm_existing", similar)
                continue
            new_name = decision.new_product_name.strip() if decision and decision.new_product_name else ""
            if not new_name:
                out[raw_name] = ResolvedProduct(raw_name, None, None, "unresolved", similar)
                continue
            product_id = self.products_repository.get_product_by_name(new_name)
            if product_id is None:
                product_id = self.products_repository.insert_product(new_name)
            if product_id is not None:
                self.products_repository.insert_alternative_name(raw_name, product_id)
            out[raw_name] = ResolvedProduct(raw_name, product_id, new_name, "llm_new", similar)
        return out
