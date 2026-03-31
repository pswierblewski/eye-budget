# Implementation Plan: Semantic Versioning Display

**Branch**: `006-semantic-versioning` | **Date**: 2026-03-31 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/specs/006-semantic-versioning/spec.md`

## Summary

Add independent semantic versioning to the frontend and backend, both starting at `1.0.0`. The backend version is exposed via a public `GET /version` endpoint; the frontend fetches it once at app startup (React Query, staleTime: Infinity) and displays both versions at the bottom of the left sidebar.

## Technical Context

**Language/Version**: TypeScript 5 / Node 20 (frontend); Python 3.11.7 (backend)  
**Primary Dependencies**: Next.js 14, React 18, @tanstack/react-query v5 (frontend); FastAPI, Pydantic v2 (backend)  
**Storage**: N/A — version is a static in-memory constant  
**Testing**: pytest + pytest-asyncio (backend); tsc + eslint (frontend)  
**Target Platform**: Linux server (Docker Compose), browser  
**Project Type**: Web application (Next.js + FastAPI)  
**Performance Goals**: Version endpoint responds in <200ms p95 (constant in-memory string, trivially satisfied)  
**Constraints**: No DB migrations needed. Frontend version baked at build time. Polish user-facing strings.  
**Scale/Scope**: Single endpoint, one sidebar component modification, no new pages

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality | ✅ PASS | `version.py` has single responsibility; no hardcoded values in source — version string lives in dedicated file and `package.json`; `NEXT_PUBLIC_FRONTEND_VERSION` exposed via `next.config.mjs` |
| II. Testing Standards | ✅ PASS | New `/version` endpoint covered by integration test; frontend `getVersionInfo()` utility covered by unit test; Sidebar rendering covered by component test |
| III. UX Consistency | ✅ PASS | User-facing labels in Polish (`ładowanie...`, `nieznana`); Tailwind only for styling; no new UI primitives needed |
| IV. Performance | ✅ PASS | Endpoint is pure in-memory; frontend caches with staleTime: Infinity |
| V. Frontend Architecture | ✅ PASS | `VersionInfoSchema` in `lib/types.ts`; `getVersionInfo()` in `lib/api.ts`; proxy route in `app/api/version/route.ts`; useQuery in Sidebar |
| VI. Backend Conventions | ✅ PASS | Route in `main.py` under `# --- System ---`; `response_model=VersionResponse`; no `App()` needed (no DB); follows `*Response` naming |

No violations — Complexity Tracking table not required.

## Project Structure

### Documentation (this feature)

```text
specs/006-semantic-versioning/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── version.md       # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks)
```

### Source Code (files touched by this feature)

```text
backend/
├── src/
│   ├── version.py          # NEW — single source of truth: VERSION = "1.0.0"
│   ├── data.py             # MODIFIED — add VersionResponse Pydantic model
│   └── main.py             # MODIFIED — add GET /version route
└── tests/
    ├── unit/
    │   └── test_version.py          # NEW — unit test for version constant
    └── integration/
        └── test_version_endpoint.py # NEW — integration test for GET /version

frontend/
├── package.json            # MODIFIED — bump version "0.1.0" → "1.0.0"
├── next.config.mjs         # MODIFIED — expose NEXT_PUBLIC_FRONTEND_VERSION from package.json
├── lib/
│   ├── types.ts            # MODIFIED — add VersionInfoSchema + VersionInfo type
│   └── api.ts              # MODIFIED — add getVersionInfo() function
├── app/api/version/
│   └── route.ts            # NEW — Next.js proxy: GET /api/version → proxyGet("/version")
└── components/
    └── Sidebar.tsx         # MODIFIED — add version display footer at bottom
```

## Implementation Sequence

### Step 1 — Backend version constant (no dependencies)
- Create `backend/src/version.py` with `VERSION = "1.0.0"`

### Step 2 — Backend Pydantic model (depends on Step 1)
- Add `VersionResponse` to `backend/src/data.py`

### Step 3 — Backend route (depends on Steps 1 & 2)
- Add `GET /version` to `backend/src/main.py` under `# --- System ---` section

### Step 4 — Backend tests (depends on Steps 1–3)
- Unit test for `VERSION` constant
- Integration test for `GET /version` response shape and status

### Step 5 — Frontend version source (no dependencies)
- Update `frontend/package.json` version `"0.1.0"` → `"1.0.0"`
- Update `frontend/next.config.mjs` to expose `NEXT_PUBLIC_FRONTEND_VERSION`

### Step 6 — Frontend types & API client (depends on Step 5)
- Add `VersionInfoSchema` + `VersionInfo` to `frontend/lib/types.ts`
- Add `getVersionInfo()` to `frontend/lib/api.ts`

### Step 7 — Next.js proxy route (depends on Step 6)
- Create `frontend/app/api/version/route.ts` using `proxyGet("/version")`

### Step 8 — Sidebar version display (depends on Steps 5–7)
- Add version footer to `frontend/components/Sidebar.tsx`
- Use `useQuery({ queryKey: ["version"], queryFn: getVersionInfo, staleTime: Infinity, gcTime: Infinity })`
- Show `process.env.NEXT_PUBLIC_FRONTEND_VERSION` for frontend version
- Show backend version from query result; fallback to `"nieznana"` on error, `"ładowanie..."` while loading

### Step 9 — Frontend type-check & lint verification
- `cd frontend && npx tsc --noEmit` — zero errors
- `cd frontend && npm run lint` — zero errors
