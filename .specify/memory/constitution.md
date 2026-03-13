<!--
SYNC IMPACT REPORT
==================
Version change: [template] → 1.0.0 (initial ratification)

Modified principles: N/A (first population from template)

Added sections:
  - Core Principles (I–IV)
  - API Contract Integrity
  - Development Workflow & Quality Gates
  - Governance

Removed sections: none

Templates requiring updates:
  - .specify/templates/plan-template.md ✅ Constitution Check placeholder is generic; gates below apply
  - .specify/templates/spec-template.md ✅ Success Criteria section already supports measurable outcomes aligned with Principle IV
  - .specify/templates/tasks-template.md ✅ Phase structure supports testing discipline required by Principle II

Follow-up TODOs:
  - None. All placeholders resolved.
-->

# Eye Budget Constitution

## Core Principles

### I. Code Quality & Separation of Concerns

Every module MUST have a single, clearly stated responsibility.
TypeScript lives exclusively in `frontend/`; Python lives exclusively in `backend/`.
Strict TypeScript (`strict: true`) MUST be maintained — no `any` casts without a
documented justification comment.
Pydantic models in `backend/src/data.py` MUST be the canonical source of truth for
all request/response shapes; no raw dict passing across service boundaries.
Functions and classes MUST be kept small and focused — a function that cannot be
described in one sentence MUST be refactored.
Dead code, commented-out blocks, and debug prints MUST NOT be committed to main.

**Rationale**: A monorepo with two heterogeneous stacks (Next.js + FastAPI) is
particularly vulnerable to cross-language pattern leakage and implicit coupling.
Strict boundaries reduce cognitive load and make each side independently deployable.

### II. Testing Standards

Every new API endpoint MUST be covered by at least one integration test that exercises
the full request → service → repository → DB round trip.
Frontend API client functions in `lib/api.ts` MUST have type coverage validated via
Zod schemas in `lib/types.ts` — schema mismatches MUST be caught at runtime boundaries.
Unit tests MUST cover all non-trivial business logic in `backend/src/services/`.
Tests MUST be written before or alongside the implementation — merging untested
business logic to main is not permitted.
All tests MUST pass (`npm run lint` + backend test suite) before a feature branch is
merged.

**Rationale**: Eye Budget processes financial data from OCR pipelines. Regressions in
transaction extraction or storage are high-impact. A disciplined test baseline prevents
silent data corruption across releases.

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

## API Contract Integrity

Every API change MUST update all four layers simultaneously:
1. `backend/src/main.py` — route definition
2. `backend/src/data.py` — Pydantic request/response models
3. `frontend/app/api/<resource>/route.ts` — Next.js proxy route handler
4. `frontend/lib/api.ts` + `frontend/lib/types.ts` — typed client function + Zod schema

Partial updates that leave any layer out of sync MUST NOT be merged.
Breaking changes to existing endpoints MUST be discussed with the team before
implementation; backward-compatible additions are preferred over field removal.

## Development Workflow & Quality Gates

Database schema changes MUST be delivered as Yoyo migration files in
`backend/migrations/`, named `YYYYMMDD_XX_description.sql`. Migrations MUST be
applied before the corresponding code change is deployed.
All PRs MUST pass:
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

All code reviews MUST verify compliance with the four Core Principles.
Complexity that violates a principle MUST be justified in the PR description with a
documented rationale; unexplained violations are grounds for rejection.

**Version**: 1.0.0 | **Ratified**: 2026-03-13 | **Last Amended**: 2026-03-13
