# Quickstart: Fix Ambiguous Column in Category Creation

**Feature**: 008-fix-category-id-ambiguity

## What changed

Single-line SQL fix in `backend/src/repositories/categories.py` — the duplicate-check query in `create_category()` now qualifies the `id` and `name` columns with the `c.` table alias to resolve a PostgreSQL ambiguity error on the self-join.

## How to verify locally

```bash
# 1. Activate virtualenv
source venv/bin/activate

# 2. Run backend tests
cd backend && python -m pytest tests/unit/test_categories_repository.py -v

# 3. Manual smoke test (backend must be running)
curl -X POST http://localhost:8001/categories \
  -H "Content-Type: application/json" \
  -d '{"name": "TestKategoria", "parent_id": null}'
# Expected: HTTP 200/201 with {"id": ..., "name": "TestKategoria", "parent_name": null}
```

## How to verify on server

```bash
ssh homeserver
docker logs eye-budget-backend-1 --tail=20 -f
# Then trigger a category creation from the UI — no "is ambiguous" error should appear
```
