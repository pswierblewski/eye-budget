# Tasks: CI/CD Pipeline for Local Network Deployment

**Input**: Design documents from `/specs/004-cicd-local-deploy/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- No test tasks — not requested in spec

## Path Conventions

This is a CI/CD infrastructure feature. Source paths are:
- `frontend/` — Next.js app
- `.github/workflows/` — GitHub Actions workflows

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prerequisite repository changes that block all subsequent work. Must complete before any Dockerfile or workflow can be built correctly.

- [ ] T001 Add `output: 'standalone'` to the `nextConfig` object in `frontend/next.config.mjs`
- [ ] T002 Create `frontend/.dockerignore` excluding `node_modules`, `.next`, `.git`, `*.md`, and `specs/` to keep the Docker build context minimal

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Files that must exist before the workflow can build and deploy the image. Both can be written in parallel once Phase 1 is complete.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Create multi-stage `frontend/Dockerfile`: stage 1 (`deps`) runs `npm ci`; stage 2 (`builder`) copies source and runs `npm run build`; stage 3 (`runner`) uses `node:20-slim`, copies `.next/standalone`, `.next/static`, and `public/`, sets `ENV NODE_ENV=production PORT=3000 HOSTNAME=0.0.0.0`, adds `HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 CMD curl -f http://localhost:3000/api/health || exit 1`, exposes port 3000, and runs `CMD ["node", "server.js"]`
- [ ] T004 [P] Create `frontend/app/api/health/route.ts` — a GET route handler that returns `NextResponse.json({ status: 'ok' })` with HTTP 200; no business logic, no external calls

**Checkpoint**: `docker build` of `frontend/` succeeds locally and `GET /api/health` returns 200 inside the container

---

## Phase 3: User Story 1 — Automatic Deployment on Push (Priority: P1) 🎯 MVP

**Goal**: Every push to `master` triggers a workflow that builds the Docker image, replaces the running container, and makes the updated app accessible at `http://192.168.1.184:3000` — with no manual steps.

**Independent Test**: Push a one-line visible text change to master; within 5 minutes, verify the change is live at `http://192.168.1.184:3000`.

### Implementation for User Story 1

- [ ] T005 [US1] Create `.github/workflows/deploy.yml` with the following structure:
  - `on: push: branches: [master]`
  - `concurrency: group: deploy-eye-budget-production, cancel-in-progress: false`
  - `timeout-minutes: 15`
  - Single job `ci-and-deploy` with `runs-on: self-hosted`
  - Steps (in order): checkout (`actions/checkout@v4`), setup Node 20 (`actions/setup-node@v4`), `npm ci` in `frontend/`, `npm run lint` in `frontend/`, `npm run build` in `frontend/`, run backend test suite (`cd backend && python -m pytest`), docker build (`docker build --build-arg NEXT_PUBLIC_API_URL=${{ secrets.NEXT_PUBLIC_API_URL }} -t eye-budget-frontend:latest ./frontend`), `docker stop eye-budget-frontend || true`, `docker rm eye-budget-frontend || true`, `docker run -d --name eye-budget-frontend -p 3000:3000 --restart unless-stopped eye-budget-frontend:latest`

- [ ] T006 [P] [US1] Perform one-time server setup per `specs/004-cicd-local-deploy/quickstart.md`: create `github-runner` user, add to `docker` group, download and configure GitHub Actions runner (`./config.sh` with labels `self-hosted,linux,eye-budget`), register as systemd service (`./svc.sh install`), and add `NEXT_PUBLIC_API_URL` as a GitHub Actions secret

**Checkpoint**: After T005 and T006 are both complete, push to master and confirm the workflow runs on the self-hosted runner and the app is reachable at `http://192.168.1.184:3000`

---

## Phase 4: User Story 2 — Deployment Status Visibility (Priority: P2)

**Goal**: A developer can determine success or failure, and the reason for any failure, from the GitHub Actions run history alone — without SSH-ing into the server.

**Independent Test**: Check the Actions tab after a push; success run shows the live URL; failed run shows which step failed and why.

### Implementation for User Story 2

- [ ] T007 [US2] Add a post-deploy health check step to `.github/workflows/deploy.yml` (after `docker run`) that polls `GET http://localhost:3000/api/health` up to 5 times with 5-second intervals using `curl --retry 5 --retry-delay 5 --retry-connrefused -f http://localhost:3000/api/health`; step name should be `Verify deployment health`

- [ ] T008 [P] [US2] Add a `workflow_dispatch` trigger to `.github/workflows/deploy.yml` alongside the existing `push` trigger, to allow manual re-triggers from the GitHub Actions UI when the server was temporarily unreachable

- [ ] T009 [P] [US2] Add a step at the end of the `ci-and-deploy` job in `.github/workflows/deploy.yml` that uses `$GITHUB_STEP_SUMMARY` to post a deployment summary: on success, write `✅ Deployed at $(date -u) — http://192.168.1.184:3000`; this step runs with `if: success()`

**Checkpoint**: After a successful push, the Actions run summary shows the live URL and timestamp. After a failed push (e.g., lint error), the failing step name and error are visible in the run log.

---

## Phase 5: User Story 3 — Safe Failure Handling (Priority: P3)

**Goal**: A deployment that fails (broken build, crashing container, or failed health check) leaves the previously working version still running on port 3000.

**Independent Test**: Introduce a deliberate runtime crash (e.g., `process.exit(1)` at startup) and push to master; after the deployment fails, verify the previous working version is still accessible at `http://192.168.1.184:3000`.

### Implementation for User Story 3

- [ ] T010 [US3] Add a step in `.github/workflows/deploy.yml` immediately before the `docker build` step that tags the currently running image as `:previous` if it exists: `docker tag eye-budget-frontend:latest eye-budget-frontend:previous 2>/dev/null || true`; step name: `Tag current image as previous`

- [ ] T011 [US3] Add a rollback step in `.github/workflows/deploy.yml` with `if: failure()` that runs after the health check step: stop and remove the newly started container, then start `eye-budget-frontend:previous` if it exists (`docker image inspect eye-budget-frontend:previous &>/dev/null && docker run -d --name eye-budget-frontend -p 3000:3000 --restart unless-stopped eye-budget-frontend:previous || echo "No previous image available — server may be down"`); step name: `Rollback to previous image`

**Checkpoint**: Force a deployment failure and confirm the rollback step runs and the previous version remains reachable at `http://192.168.1.184:3000`

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Operational hygiene and final validation

- [ ] T012 Add a maintenance note to `specs/004-cicd-local-deploy/quickstart.md` documenting the weekly `docker image prune -f` cron for the `github-runner` user: `0 3 * * 0 docker image prune -f --filter "until=168h"` (this keeps `:latest` and `:previous` but removes untagged intermediate layers)

- [ ] T013 End-to-end validation: follow `specs/004-cicd-local-deploy/quickstart.md` from Step 1 to Step 5 on the Debian server, push a visible UI text change to master, and confirm all five success criteria from `specs/004-cicd-local-deploy/spec.md` are met (SC-001 through SC-005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 (standalone mode must be set before Dockerfile is written)
- **US1 (Phase 3)**: Depends on Phase 2 — both T003 and T004 must exist before the workflow can reference the Dockerfile and health endpoint
- **US2 (Phase 4)**: Depends on US1 baseline workflow existing (T005 must be complete)
- **US3 (Phase 5)**: Depends on US1 (needs running container to tag as `:previous`) and US2 health check step (T007) to know when the rollback should trigger
- **Polish (Phase 6)**: Depends on all story phases being complete

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no dependency on US2 or US3
- **US2 (P2)**: Depends on US1 workflow file existing (adds steps to `.github/workflows/deploy.yml`)
- **US3 (P3)**: Depends on US1 (running container) and the health check step from US2 (T007) to trigger the rollback condition

### Within Each Phase

- T003 and T004 are independent (different files) — fully parallel
- T006 (server setup) is independent of T005 (workflow writing) — fully parallel within US1
- T007, T008, T009 within US2 are all independent (different steps/triggers) — fully parallel
- T010 and T011 within US3 have an order dependency: T010 (tag step) must be positioned before T011 (rollback step) in the workflow YAML

### Parallel Opportunities

- T003 + T004 can be done simultaneously (Dockerfile vs health route)
- T005 + T006 can be done simultaneously (write workflow vs set up server)
- T007 + T008 + T009 can be done simultaneously (all add to deploy.yml but in different places/triggers)

---

## Parallel Example: User Story 1

```bash
# These two tasks are fully independent — start both simultaneously:
Task T005: "Create .github/workflows/deploy.yml with CI + deploy steps"
Task T006: "Perform one-time server setup per quickstart.md"

# Both must complete before end-to-end test of US1
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001, T002)
2. Complete Phase 2: Foundational (T003, T004 in parallel)
3. Complete Phase 3: US1 (T005, T006 in parallel)
4. **STOP and VALIDATE**: Push a visible change, confirm it deploys automatically to `http://192.168.1.184:3000`
5. Pipeline is live and useful — US2 and US3 are enhancements

### Incremental Delivery

1. Phases 1 + 2 → Docker image builds correctly
2. Phase 3 (US1) → Automatic deployment works (MVP)
3. Phase 4 (US2) → Status visibility and manual re-trigger added
4. Phase 5 (US3) → Rollback safety net added
5. Phase 6 → Operations polished

### Single Developer Order

1. T001 → T002 → T003 + T004 (parallel) → T005 + T006 (parallel) → validate US1
2. T007 + T008 + T009 (parallel) → validate US2
3. T010 → T011 → validate US3
4. T012 → T013

---

## Notes

- [P] tasks = different files or independent workflow additions, no dependencies between them
- T005 and T006 are the only tasks that both modify `.github/workflows/deploy.yml` and the server respectively — coordinate to avoid editing the same workflow file simultaneously
- T007, T008, T009 all modify `.github/workflows/deploy.yml` — if done simultaneously, coordinate on a shared branch or sequential edits to avoid merge conflicts
- Server setup (T006) is a one-time operator action — it is not automated by the pipeline itself
- The `NEXT_PUBLIC_API_URL` secret must be set in GitHub before the first deployment (required by T005 workflow step)
- Verify `npm run lint`, `npm run build`, and backend tests all pass locally before pushing (the pipeline will enforce these but faster to catch early)
