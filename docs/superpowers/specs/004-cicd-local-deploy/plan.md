# Implementation Plan: CI/CD Pipeline for Local Network Deployment

**Branch**: `004-cicd-local-deploy` | **Date**: 2026-03-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-cicd-local-deploy/spec.md`

## Summary

Add an automated GitHub Actions CI/CD pipeline that deploys the Next.js frontend to a self-hosted Debian server (192.168.1.184) on every push to `master`. The pipeline runs lint/build/test checks, builds a Docker image using a multi-stage standalone Dockerfile, and deploys it via the local Docker daemon (runner and server are the same machine). Deployments are serialised via GitHub Actions concurrency queuing; a post-deploy health check with automatic rollback to the previous image protects against broken deployments.

## Technical Context

**Language/Version**: GitHub Actions YAML, Dockerfile (Node 20 / node:20-slim), TypeScript 5 / Node 20 (Next.js 14)
**Primary Dependencies**: GitHub Actions self-hosted runner, Docker (already on server), Node 20
**Storage**: N/A
**Testing**: `npm run lint`, `npm run build`, backend test suite (pre-deploy gates per constitution); Docker HEALTHCHECK + curl smoke test (post-deploy gate)
**Target Platform**: Debian Linux x64 (192.168.1.184), GitHub Actions runner environment
**Project Type**: CI/CD pipeline for a web application (Next.js frontend service)
**Performance Goals**: Full pipeline (checks + build + deploy) completes within 15 minutes; new version live within 5 minutes of a successful build
**Constraints**: Server not internet-accessible; runner installed on the same Debian server; no image registry needed; port 3000; Docker must be used
**Scale/Scope**: Single server, single container (`eye-budget-frontend`), single environment (local LAN)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Code Quality & Separation of Concerns | ✅ PASS | No hardcoded credentials, URLs, or ports in source files — all via GitHub Secrets and env vars. New files are single-responsibility (Dockerfile builds image; workflow deploys it). |
| II | Testing Standards | ✅ PASS | Pipeline enforces `npm run lint`, `npm run build`, and backend test suite as required pre-deploy gates. New `app/api/health/route.ts` is trivially simple (no conditional logic); type coverage via TypeScript strict mode is sufficient. |
| III | UX Consistency | ✅ N/A | No user-facing UI changes. |
| IV | Performance | ✅ PASS | `npm run build` must complete without errors (enforced by pipeline). Multi-stage standalone image keeps build fast and repeatable. |
| V | Frontend Architecture | ✅ PASS | New `app/api/health/route.ts` is a simple route handler returning a static JSON response — no business logic, no DB access, follows constitution conventions. |
| VI | Backend Conventions | ✅ N/A | No backend code changes. |
| Secrets | No secrets committed | ✅ PASS | All credentials via GitHub Secrets; `.env` and `yoyo.ini` not touched. |
| Dirs | No new top-level dirs | ✅ PASS | `.github/workflows/` is within the existing `.github/` directory; `frontend/Dockerfile` is within `frontend/`. |

**Post-design re-check**: No violations introduced. No complexity table entry required.

## Project Structure

### Documentation (this feature)

```text
specs/004-cicd-local-deploy/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output — server setup instructions
└── tasks.md             # Phase 2 output (tasks.md)
```

### Source Code (repository root)

```text
.github/
└── workflows/
    └── deploy.yml           # NEW — GitHub Actions CI/CD workflow

frontend/
├── app/
│   └── api/
│       └── health/
│           └── route.ts     # NEW — health check endpoint for post-deploy probe
├── Dockerfile               # NEW — multi-stage Next.js standalone build
└── next.config.mjs          # MODIFIED — add output: 'standalone'
```

**Structure Decision**: All new files are within existing directories. No new top-level directories are created. Backend is not touched (frontend-only deployment scope per spec).

## Implementation Phases

### Phase A: Next.js Frontend Docker Support

**Goal**: Make the frontend buildable as a standalone Docker image.

**Changes**:
1. `frontend/next.config.mjs` — add `output: 'standalone'`.
2. `frontend/Dockerfile` — multi-stage build (deps → builder → runner stages, `node:20-slim`).
3. `frontend/app/api/health/route.ts` — trivial route returning `{ status: 'ok' }` with HTTP 200. Used by Docker `HEALTHCHECK` and the pipeline smoke test.

**Dockerfile design**:
```
Stage 1 (deps):    node:20-slim, npm ci
Stage 2 (builder): node:20-slim, copy deps, copy source, npm run build
Stage 3 (runner):  node:20-slim, copy .next/standalone, .next/static, public/, expose 3000, CMD node server.js
```

**Docker HEALTHCHECK** (in Dockerfile):
```
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1
```

**Environment variables**:
- `NEXT_PUBLIC_API_URL` — passed as a Docker build arg; baked into the bundle. Value sourced from GitHub Secret.
- `NODE_ENV=production`, `PORT=3000`, `HOSTNAME=0.0.0.0` — set in Dockerfile.

---

### Phase B: GitHub Actions Workflow

**Goal**: Define the CI/CD pipeline that triggers on master push, runs checks, and deploys.

**File**: `.github/workflows/deploy.yml`

**Workflow structure**:
```
Trigger:      push to master
Concurrency:  group=deploy-eye-budget-production, cancel-in-progress=false
Runner:       self-hosted (installed on Debian server)
Timeout:      15 minutes

Job: ci-and-deploy
  Step 1:  Checkout code
  Step 2:  Set up Node 20
  Step 3:  npm ci (frontend)
  Step 4:  npm run lint (frontend) — fail fast
  Step 5:  npm run build (frontend) — fail fast (also validates standalone output)
  Step 6:  Backend test suite (cd backend && python -m pytest)
  Step 7:  Tag current image as :previous (if it exists) — rollback anchor
  Step 8:  docker build -t eye-budget-frontend:latest ./frontend
             --build-arg NEXT_PUBLIC_API_URL=${{ secrets.NEXT_PUBLIC_API_URL }}
  Step 9:  docker stop eye-budget-frontend || true
  Step 10: docker rm eye-budget-frontend || true
  Step 11: docker run -d --name eye-budget-frontend
             -p 3000:3000 --restart unless-stopped
             eye-budget-frontend:latest
  Step 12: Health check — poll GET http://localhost:3000/api/health (retry 5×, 5s apart)
  Step 13: On failure → rollback step:
             docker stop eye-budget-frontend || true
             docker rm eye-budget-frontend || true
             docker run -d --name eye-budget-frontend -p 3000:3000 --restart unless-stopped eye-budget-frontend:previous
             (only runs if :previous tag exists; otherwise just reports failure)
```

**Rollback trigger**: Step 12 failure exits non-zero. A subsequent step with `if: failure()` performs the rollback.

---

### Phase C: Server Setup (one-time, documented)

**Goal**: Prepare the Debian server to receive deployments.

**Steps** (fully documented in `quickstart.md`):
1. Create `github-runner` user, add to `docker` group.
2. Download and configure GitHub Actions runner (`./config.sh`).
3. Register as systemd service (`./svc.sh install`).
4. Set GitHub Secret `NEXT_PUBLIC_API_URL`.
5. Add weekly `docker image prune -f` cron to avoid disk accumulation.

These steps are operator actions — not automated by the pipeline. They are one-time setup only.

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Runner location | Same Debian server as deployment target | Eliminates image transfer; simplest topology for single-server home lab |
| Image registry | None — local Docker daemon only | No internet access needed; runner is on the same machine |
| Rollback mechanism | Tag `:previous` before deploy, restore on health check failure | Simple, no external state; works without a registry |
| Concurrent deployment handling | Queue (`cancel-in-progress: false`) | Guarantees commit ordering; no mid-deploy race conditions |
| Server unreachable | Fail fast — no retries | Visible failure in pipeline history; developer re-triggers manually |
| Base image | `node:20-slim` | glibc compatibility; stable with npm native extensions |
| Port | 3000 | As clarified by user; Next.js default |

## Acceptance Verification

| Success Criterion | How to verify |
|---|---|
| SC-001: Deploy within 5 min, no manual steps | Push a visible text change to master; check app at http://192.168.1.184:3000 |
| SC-002: 100% of successful builds deploy | Check Actions history — no successful build run without a corresponding deployment |
| SC-003: Success/failure visible without SSH | Review Actions run logs on GitHub for clear pass/fail and error messages |
| SC-004: Failed deploy leaves previous version running | Push a build that crashes on startup; verify old version still serves at :3000 |
| SC-005: Reproducible from repo + quickstart.md | Follow quickstart.md on a fresh Debian machine and verify end-to-end |
