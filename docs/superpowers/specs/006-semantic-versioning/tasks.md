# Tasks: Semantic Versioning Display

**Input**: Design documents from `/specs/006-semantic-versioning/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Integration and unit tests included per constitution (Principle II — all new code must have tests).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to ([US1], [US2])

---

## Phase 1: Setup (Version Sources)

**Purpose**: Establish the single authoritative version source for each component. These are pure file-creation tasks with no inter-dependencies.

- [x] T001 Create `backend/src/version.py` with `VERSION = "1.0.0"` as the backend version constant
- [x] T002 [P] Update `frontend/package.json` field `"version"` from `"0.1.0"` to `"1.0.0"`

**Checkpoint**: Both version constants are defined. No runtime code yet.

---

## Phase 2: Foundational (API Contract — All 4 Layers)

**Purpose**: Wire the full API contract as required by the constitution (API Contract Integrity section). All 4 layers must be implemented together before the sidebar can be built.

**⚠️ CRITICAL**: The sidebar (US1) cannot be implemented until all layers here are complete.

- [x] T003 Add `VersionResponse(BaseModel)` Pydantic model with fields `version: str` and `component: str` to `backend/src/data.py` (follow `*Response` naming convention, place at bottom of file)
- [x] T004 [P] Add `VersionInfoSchema = z.object({ version: z.string(), component: z.string() })` and `export type VersionInfo = z.infer<typeof VersionInfoSchema>` to `frontend/lib/types.ts`
- [x] T005 Add `GET /version` route to `backend/src/main.py` under a new `# --- System ---` section comment; import `VERSION` from `src.version` and `VersionResponse` from `src.data`; declare `response_model=VersionResponse`; return `VersionResponse(version=VERSION, component="backend")` — no `App()` needed
- [x] T006 [P] Update `frontend/next.config.mjs` to read `package.json` version at build time and expose it as `env.NEXT_PUBLIC_FRONTEND_VERSION`
- [x] T007 Create `frontend/app/api/version/route.ts` with `export async function GET() { return proxyGet("/version"); }` importing `proxyGet` from `@/lib/proxy`
- [x] T008 Add `getVersionInfo()` async function to `frontend/lib/api.ts`: calls `apiFetch("/api/version", VersionInfoSchema)`, importing `VersionInfo`, `VersionInfoSchema` from `@/lib/types`

**Checkpoint**: `GET /version` is reachable and returns `{"version": "1.0.0", "component": "backend"}`. Frontend has a typed `getVersionInfo()` client. Now US1 can begin.

---

## Phase 3: User Story 1 — View Current Application Versions (Priority: P1) 🎯 MVP

**Goal**: Both version numbers visible in the sidebar footer on every page of the app.

**Independent Test**: Run the app, open any page, check the bottom of the left sidebar for "Frontend: v1.0.0" and "Backend: v1.0.0". Stop the backend and confirm "Backend: nieznana" appears without crashing.

### Tests for User Story 1

- [x] T009 [P] [US1] Write unit test for `VERSION` constant in `backend/tests/unit/test_version.py`: import `VERSION` from `src.version`, assert it equals `"1.0.0"` and matches semver pattern `^\d+\.\d+\.\d+$`
- [x] T010 [P] [US1] Write integration test for `GET /version` in `backend/tests/integration/test_version_endpoint.py`: assert HTTP 200, `response.json()["version"] == "1.0.0"`, `response.json()["component"] == "backend"`, and the endpoint requires no authentication

### Implementation for User Story 1

- [x] T011 [US1] Add version display footer to `frontend/components/Sidebar.tsx`: import `useQuery` from `@tanstack/react-query` and `getVersionInfo` from `@/lib/api`; add `useQuery({ queryKey: ["version"], queryFn: getVersionInfo, staleTime: Infinity, gcTime: Infinity, retry: 1 })`; render a `<footer>` element after the closing `</nav>` tag inside the `<aside>`, with `px-6 py-3 border-t border-gray-200` styling; show two lines using `text-[10px] text-gray-400` matching existing sidebar label style:
  - Line 1: `Frontend: v{process.env.NEXT_PUBLIC_FRONTEND_VERSION ?? "?"}`
  - Line 2: `Backend: v{isLoading ? "ładowanie..." : (data?.version ?? "nieznana")}`

**Checkpoint**: User Story 1 fully functional. Both versions visible in sidebar. Backend-down fallback works. MVP deliverable.

---

## Phase 4: User Story 2 — Increment Version on New Release (Priority: P2)

**Goal**: Developer can bump frontend or backend version independently and see the new version in the sidebar after redeployment.

**Independent Test**: Change `backend/src/version.py` `VERSION` to `"1.0.1"`, restart backend — sidebar shows "Backend: v1.0.1" while "Frontend: v1.0.0" is unchanged. Then change `frontend/package.json` `version` to `"1.1.0"`, rebuild frontend — sidebar shows "Frontend: v1.1.0" while backend shows the previous value. Revert both back to `1.0.0`.

### Implementation for User Story 2

- [x] T012 [US2] Verify independent version bumping: temporarily set `VERSION = "1.0.1"` in `backend/src/version.py` and run `python -m pytest backend/tests/unit/test_version.py` — update the test assertion to `"1.0.1"` to confirm the mechanism works, then revert both `version.py` and the test back to `"1.0.0"`

**Checkpoint**: Developer has confidence that editing one file changes exactly one component's version with no side effects.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Quality gates required by the constitution before merge.

- [x] T013 [P] Run `cd frontend && npx tsc --noEmit` — confirm zero TypeScript errors; fix any type issues surfaced by the new `VersionInfo` type or `process.env.NEXT_PUBLIC_FRONTEND_VERSION` usage
- [x] T014 [P] Run `cd frontend && npm run lint` — confirm zero ESLint errors; fix any issues in `Sidebar.tsx`, `api/version/route.ts`, or `lib/api.ts`
- [x] T015 Run `cd backend && python -m pytest` — confirm all backend tests pass including new version tests

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** (Setup): No dependencies — start immediately; T001 and T002 fully parallel
- **Phase 2** (Foundational): Depends on Phase 1 — T003 depends on T001; T004/T006 depend on T002; T005 depends on T003; T007/T008 depend on T004 and T005
- **Phase 3** (US1): Depends on Phase 2 completion — T009/T010 parallel; T011 depends on T009/T010 by convention (tests first)
- **Phase 4** (US2): Depends on Phase 3 — requires the infrastructure to be running
- **Phase 5** (Polish): Depends on Phases 3 and 4

### Within Phase 2 — Execution Order

```
T001 (version.py) ──→ T003 (VersionResponse) ──→ T005 (GET /version route)
                                                        ↓
T002 (package.json) → T004 (VersionInfoSchema) → T007 (proxy route) → T008 (getVersionInfo)
T002 (package.json) → T006 (next.config.mjs)  [parallel with T004]
```

### Parallel Opportunities

- T001 + T002 — fully parallel (different files, different stacks)
- T003 + T004 — parallel (Python vs TypeScript)
- T004 + T006 — parallel (both depend on T002, different files)
- T009 + T010 — parallel (different test files)
- T013 + T014 — parallel (both are read-only checks)

---

## Parallel Example: Phase 2

```bash
# After T001 and T002 complete, launch these in parallel:
Task T003: "Add VersionResponse to backend/src/data.py"
Task T004: "Add VersionInfoSchema to frontend/lib/types.ts"
Task T006: "Update frontend/next.config.mjs"

# After T003 completes:
Task T005: "Add GET /version route to backend/src/main.py"

# After T004 and T005 complete:
Task T007: "Create frontend/app/api/version/route.ts"
Task T008: "Add getVersionInfo() to frontend/lib/api.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001, T002)
2. Complete Phase 2: Foundational (T003–T008)
3. Complete Phase 3: User Story 1 tests + implementation (T009–T011)
4. **STOP and VALIDATE**: Both versions visible in sidebar, fallback works
5. Deploy — this is a complete, working increment

### Incremental Delivery

1. Phase 1 + 2 → API contract complete (backend endpoint works, frontend client typed)
2. Phase 3 → Versions visible in UI — **MVP ready to ship**
3. Phase 4 → Bump workflow validated
4. Phase 5 → Quality gates pass → merge to master

---

## Notes

- [P] tasks operate on different files with no shared dependencies
- [US1] / [US2] labels map tasks to spec.md user stories for traceability
- Constitution requirement: all new backend code in `backend/src/data.py` + `main.py`; all frontend API code in `lib/api.ts` + `lib/types.ts`
- `NEXT_PUBLIC_FRONTEND_VERSION` is baked at build time — changes to `package.json` require a frontend rebuild to take effect
- `VERSION` in `backend/src/version.py` takes effect immediately on backend restart — no rebuild needed
- Commit after T002 (both version constants set), after T008 (full API contract wired), after T011 (US1 complete)
