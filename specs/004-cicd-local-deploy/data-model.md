# Data Model: CI/CD Pipeline for Local Network Deployment

**Phase 1 Output** | Feature: `004-cicd-local-deploy` | Date: 2026-03-21

No persistent data model changes are introduced by this feature. The pipeline is infrastructure-only.

---

## Configuration Entities

These are file-based entities (not database entities) that define the pipeline and deployment.

### GitHub Actions Workflow (`deploy.yml`)

| Field | Value / Description |
|-------|---------------------|
| Trigger | `push` to `master` branch |
| Concurrency group | `deploy-eye-budget-production` |
| Cancel in progress | `false` (queue, do not cancel) |
| Runner label | `self-hosted` (installed on Debian server) |
| Timeout | 15 minutes |
| Stages | CI checks → build image → deploy → health check → rollback on failure |

### Docker Image

| Field | Value / Description |
|-------|---------------------|
| Name | `eye-budget-frontend` |
| Tags | `latest` (current deploy), `previous` (last known good) |
| Base image | `node:20-slim` |
| Build context | `frontend/` |
| Exposed port | `3000` |
| Build args | `NEXT_PUBLIC_API_URL` (baked at build time) |

### Running Container

| Field | Value / Description |
|-------|---------------------|
| Container name | `eye-budget-frontend` |
| Port binding | `3000:3000` |
| Restart policy | `unless-stopped` |
| Health check path | `GET /api/health` |
| Expected response | HTTP 200, `{ "status": "ok" }` |

### GitHub Secrets Required

| Secret name | Purpose |
|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL baked into the Next.js bundle at build time |

> Note: No SSH keys are required since the runner runs on the same machine as the deployment target.
