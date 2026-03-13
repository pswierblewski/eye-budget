<!--
SYNC IMPACT REPORT
==================
Version change: 1.1.0 → 1.2.0 (MINOR — two new principles added; Principles I and III expanded)

Modified principles:
  - I. Code Quality & Separation of Concerns: clarified TypeScript and Python
    discipline; no change to non-negotiables, added precision on hardcoded values.
  - III. User Experience Consistency: expanded with full design token inventory,
    styling rules, icon library constraint, and form handling patterns.

Added sections:
  - V. Frontend Architecture & Design System (new principle)
  - VI. Backend Conventions (new principle)

Removed sections: none

Templates requiring updates:
  - .specify/templates/plan-template.md ✅ Constitution Check placeholder is generic; gates below apply
  - .specify/templates/spec-template.md ✅ Success Criteria section already supports measurable outcomes aligned with Principle IV
  - .specify/templates/tasks-template.md ✅ Phase structure supports testing discipline required by Principle II

Follow-up TODOs:
  - Existing codebase unit-test coverage is acknowledged as a known gap.
    A dedicated backlog task to retrofit unit tests for existing services is recommended.
-->

# Eye Budget Constitution

## Core Principles

### I. Code Quality & Separation of Concerns

Every module MUST have a single, clearly stated responsibility.
TypeScript lives exclusively in `frontend/`; Python lives exclusively in `backend/`.
Strict TypeScript (`"strict": true` in `tsconfig.json`) MUST be maintained.
`any` casts MUST NOT be used without an inline comment explaining why the type is
unknowable — silent `any` is never acceptable.
Pydantic models in `backend/src/data.py` MUST be the canonical source of truth for
all request/response shapes; no raw dict passing across service boundaries.
Functions and classes MUST be kept small and focused — a function that cannot be
described in one sentence MUST be refactored.
Dead code, commented-out blocks, and debug prints MUST NOT be committed to main.
No hardcoded URLs, API keys, credentials, hostnames, or ports in source files — all
config MUST be read from environment variables.

**Rationale**: A monorepo with two heterogeneous stacks (Next.js + FastAPI) is
particularly vulnerable to cross-language pattern leakage and implicit coupling.
Strict boundaries reduce cognitive load and make each side independently deployable.

### II. Testing Standards

**⚠ Known gap**: The existing codebase may lack unit test coverage in places.
This is acknowledged as technical debt. It does NOT grant permission to add more
untested code — it is a backlog item to be addressed incrementally.

Every piece of **new code** — whether it is a new feature, a bug fix, a refactor, or
a patch — MUST be accompanied by unit tests before merging. No exceptions.
Unit tests MUST cover:
- All non-trivial functions and methods in `backend/src/services/`, `backend/src/repositories/`, and `backend/src/tasks/`.
- All utility functions in `frontend/lib/` that contain conditional logic.
- All React components that contain non-trivial state logic or conditional rendering.

Every new API endpoint MUST additionally be covered by at least one integration test
that exercises the full request → service → repository → DB round trip.
Frontend API client functions in `lib/api.ts` MUST have type coverage validated via
Zod schemas in `lib/types.ts` — schema mismatches MUST be caught at runtime boundaries.
Tests MUST be written before or alongside the implementation — merging untested code
to main is not permitted.
All tests MUST pass (`npm run lint` + backend test suite) before a feature branch is
merged.

**Rationale**: Eye Budget processes financial data from OCR pipelines. Regressions in
transaction extraction or storage are high-impact. The existing test gap is a known
risk; halting its growth is the minimum viable safeguard while the backlog is addressed.

### III. User Experience Consistency

All user-facing strings MUST be written in Polish.
UI components MUST be sourced from the design-system primitives exported by
`frontend/components/ui/index.ts`. New primitives MUST NOT be created without first
confirming no equivalent exists.
Navigation, loading states, and error feedback MUST follow the established patterns:
real-time progress via Soketi/Pusher WebSocket; optimistic UI updates via
`@tanstack/react-query` mutations; error toasts/messages using existing Badge/Modal
primitives.
Long-running operations (OCR processing, evaluation) MUST always return HTTP 202
immediately and stream progress to the frontend — never block the UI with a spinner
waiting for a synchronous response.

**Rationale**: Consistent UX reduces user confusion and support burden. The Polish
language requirement is non-negotiable as the app targets Polish-speaking households.
The Celery + Soketi pattern is already proven in production; deviating from it for
new long-running tasks introduces unnecessary complexity.

### IV. Performance Requirements

FastAPI endpoints MUST respond within **200 ms p95** for all synchronous read
operations (list/get), measured under normal load.
Database queries MUST use appropriate indexes; any query doing a sequential scan on
a table with >1 000 expected rows MUST include a justification or a migration adding
the index.
Background Celery tasks MUST be idempotent — they MUST be safe to retry without
producing duplicate records or side effects.
Frontend pages MUST achieve a Largest Contentful Paint (LCP) of **≤ 2.5 s** on a
standard broadband connection; images uploaded to MinIO MUST be served with
appropriate cache headers.
The Next.js build (`npm run build`) MUST complete without errors and MUST NOT
introduce new bundle-size regressions exceeding 10 % on any route chunk.

**Rationale**: Eye Budget is an interactive financial tool used daily. Slow feedback
loops reduce trust and adoption. Idempotent Celery tasks are essential given Redis
broker restarts and at-least-once delivery semantics.

### V. Frontend Architecture & Design System

**Routing**: App Router only (`frontend/app/`). The `pages/` directory MUST NOT be
created. All page and leaf route components are `"use client"` — do not use React
Server Components for pages that display dynamic data.

**API proxy layer**: Every Next.js route handler in `app/api/` is a thin proxy that
calls one of `proxyGet`, `proxyPost`, `proxyPut`, `proxyPatch`, `proxyDelete` from
`lib/proxy.ts`. Business logic, validation, and DB access MUST NOT appear in route
handlers.

**Data fetching**: All client-side data fetching uses `@tanstack/react-query v5`
(`useQuery` / `useMutation`). Direct `fetch` calls from components or pages are
forbidden — all API calls MUST go through a typed function in `frontend/lib/api.ts`.
After every successful mutation, `queryClient.invalidateQueries()` MUST be called to
keep the cache fresh.

**Types**: Zod schemas in `frontend/lib/types.ts` are the single source of truth for
all data shapes. TypeScript types MUST be inferred via `z.infer<typeof Schema>` —
writing parallel `interface` or `type` aliases manually is forbidden. All schemas
MUST live in `lib/types.ts`; scattering schema definitions across components is
not permitted. Every `apiFetch` call MUST validate the response with `schema.parse()`
— `as SomeType` casts on raw fetch responses MUST NOT be used.

**Forms**: This project does NOT use react-hook-form, Formik, or any form library.
Forms MUST be built with controlled React inputs and `useState`. Input and date
fields MUST use `Input`, `Textarea`, and `DateInput` from `@/components/ui`.

**Styling**: Tailwind CSS is the only permitted styling mechanism. Inline `style={{}}`
MUST NOT be used except where Tailwind cannot express the value (document the
exception). Conditional class composition MUST use `clsx` — never `tailwind-merge`.

**Design tokens** (defined in `tailwind.config.ts` — use the token, never hardcode):
- Accent color: `bg-accent` / `text-accent` / `border-accent` → `#635bff`;
  hover: `bg-accent-hover` → `#5248db`. `#635bff` MUST NOT appear literally in code.
- Sidebar background: `bg-sidebar` → `#f6f9fc`.
- Status colors: `bg-status-{pending,processing,done,failed,to_confirm}` and
  `text-status-{…}`.
- Font: Inter (`fontFamily.sans`). No other font MUST be imported.

**Icons**: `lucide-react` is the only permitted icon library. Other icon packages MUST
NOT be installed. Import individual icons:
`import { ChevronRight, Plus } from "lucide-react"`.

**Component variants**: New components that need variants MUST follow the
`Record<Variant, string>` pattern used in `Button.tsx` and `Input.tsx`.

**Path alias**: `@/*` maps to `frontend/*`. All intra-project imports MUST use this
alias; relative `../..` paths across feature boundaries are not permitted.

**Navigation**: Internal links MUST use Next.js `<Link>`; programmatic navigation
MUST use `useRouter()` from `next/navigation`.

**Pusher cleanup**: WebSocket subscriptions opened in `useEffect` MUST be cleaned up
in the effect teardown via `channel.unbind_all()` and `pusherClient.unsubscribe()`.

**Canonical references (authoritative implementation examples):**
- `frontend/components/ui/index.ts` — full primitive export list
- `frontend/tailwind.config.ts` — design tokens
- `frontend/lib/api.ts` — `apiFetch` and domain API functions
- `frontend/lib/types.ts` — Zod schemas and `paginatedSchema` helper
- `frontend/lib/proxy.ts` — proxy helpers
- `frontend/lib/pusher.ts` — Pusher client
- `frontend/app/bank-transactions/page.tsx` — list page with Pusher + mutations
- `frontend/components/ui/Button.tsx` — variant + size pattern reference

**Rationale**: A consistent frontend architecture minimises onboarding friction and
prevents parallel patterns proliferating across a large component tree. The design
token system ensures visual consistency without per-component hardcoded values.

### VI. Backend Conventions

**Route organisation**: All FastAPI routes MUST live in `backend/src/main.py`.
`APIRouter` sub-packages MUST NOT be created. Routes MUST be grouped by domain with
comment headers (e.g., `# --- Receipts ---`). Every route decorator MUST declare
`response_model=` — returning raw dicts is forbidden.

**App lifecycle**: `App` (in `src/app.py`) MUST be instantiated once per HTTP request
and disposed in a `finally` block. It MUST NOT be stored as a module-level global.
`App.__init__` creates the DB context, repositories, and services. `App.dispose()`
closes the DB connection and all resources — it MUST always be called.

**Services**: Services in `src/services/` receive dependencies via constructor
injection — no globals, no `App()` inside a service. Services that preload data MUST
expose a `build()` method called in `App.__init__`. Celery tasks MUST follow the same
App lifecycle pattern as HTTP handlers.

**Pydantic model naming** (all models in `src/data.py`):
- `*ListItem` — compact shape for list responses
- `*Detail` — full shape for single-resource GET
- `*Request` — generic inbound body
- `Create*` — POST creation body
- `Update*` — PUT/PATCH body
- `*Response` — any other response shape

**Error handling**: HTTP layer errors MUST be raised as `HTTPException` with the
following status codes: `404` when a repository returns `None`; `409` when business
logic raises `ValueError`; `500` for any unhandled `Exception`. The `detail` field
MUST be `str(e)` — stack traces MUST NOT be exposed.

**Repository / SQL rules**:
- Parameterized queries only (`%s` placeholders). f-strings and `.format()` for query
  values are forbidden (SQL injection risk).
- `conn.commit()` MUST follow every successful write. `conn.rollback()` MUST appear
  in every `except` block that follows a write.
- Repositories MUST return safe fallbacks (`None`, `False`, `[]`) on error and MUST
  log the failure — re-raising from repository methods is not permitted.
- Write methods MUST guard against a missing connection at their top:
  `if not self.conn: return None`.
- Use `ON CONFLICT … DO NOTHING RETURNING id` for inserts that may race.

**Migrations**:
- File naming: `YYYYMMDD_XX_short-description.sql`.
- Every migration MUST declare `-- depends: <previous-migration-basename>`.
- All DDL MUST use safety guards: `CREATE TABLE IF NOT EXISTS`,
  `ADD COLUMN IF NOT EXISTS`, `DROP COLUMN IF EXISTS`, `CREATE INDEX IF NOT EXISTS`.
- One concern per migration file — never bundle unrelated changes.
- Applied migrations MUST NOT be modified — create a new file instead.

**Canonical references:**
- `backend/src/main.py` — route definitions, App lifecycle, error handling
- `backend/src/app.py` — App wiring and dispose pattern
- `backend/src/data.py` — Pydantic models and naming conventions
- `backend/src/services/categories.py` — service with `build()` preloading
- `backend/src/repositories/receipts_scans.py` — commit/rollback, dynamic filters
- `backend/migrations/20241010_01_receipts_scans.sql` — migration style

**Rationale**: Consistent service and repository patterns make the backend predictable
and safe to extend. Parameterized queries eliminate SQL injection. The App lifecycle
pattern ensures no leaked DB connections under any error condition.

## API Contract Integrity

Every API change MUST update all four layers simultaneously:
1. `backend/src/main.py` — route definition
2. `backend/src/data.py` — Pydantic request/response models
3. `frontend/app/api/<resource>/route.ts` — Next.js proxy route handler
4. `frontend/lib/api.ts` + `frontend/lib/types.ts` — typed client function + Zod schema

Partial updates that leave any layer out of sync MUST NOT be merged.
Breaking changes to existing endpoints MUST be discussed with the team before
implementation; backward-compatible additions are preferred over field removal.
Pagination responses MUST use the `PaginatedResponse[T]` shape on the backend and
`paginatedSchema<T>()` on the frontend: `{ items, total, limit, offset }`.

## Development Workflow & Quality Gates

Database schema changes MUST be delivered as Yoyo migration files in
`backend/migrations/`, named `YYYYMMDD_XX_description.sql`. Migrations MUST be
applied before the corresponding code change is deployed.
All PRs MUST pass:
- `cd frontend && npx tsc --noEmit` — zero TypeScript errors
- `npm run lint` (frontend) — zero errors
- `npm run build` (frontend) — zero errors
- Backend test suite — zero failures
- No `.env` or `yoyo.ini` modifications

Secrets (`.env`, `backend/yoyo.ini`) MUST never be committed, read in agent sessions,
or modified without explicit operator approval.
New top-level directories MUST NOT be created without prior team discussion.

## Governance

This constitution supersedes all other informal practices and agreements.
Amendments require:
1. A written proposal describing the change and its rationale.
2. A version bump following semantic versioning:
   - **MAJOR**: removal or redefinition of a principle or governance rule.
   - **MINOR**: new principle, new section, or materially expanded guidance.
   - **PATCH**: clarification, wording improvement, or typo fix.
3. Update of `LAST_AMENDED_DATE` and the Sync Impact Report.
4. Propagation of changes to affected templates in `.specify/templates/`.

All code reviews MUST verify compliance with the six Core Principles.
Complexity that violates a principle MUST be justified in the PR description with a
documented rationale; unexplained violations are grounds for rejection.

**Version**: 1.2.0 | **Ratified**: 2026-03-13 | **Last Amended**: 2026-03-13
