# Research: CI/CD Pipeline for Local Network Deployment

**Phase 0 Output** | Feature: `004-cicd-local-deploy` | Date: 2026-03-21

---

## 1. Self-Hosted GitHub Actions Runner on Debian

**Decision**: Install the self-hosted runner directly on the Debian server (192.168.1.184).

**Rationale**: Since the runner and the deployment target are the same machine, the runner can invoke Docker commands directly via the local Docker daemon — no SSH tunnelling, no image transfer over the network, no registry required. This is the simplest and most reliable topology for a single home-lab server.

**Alternatives considered**:
- Separate runner machine on the LAN — unnecessary complexity for a single-server setup.
- Cloud runner with SSH tunnel (ngrok, Cloudflare Tunnel) — adds external dependency, contradicts the local-only constraint.

**Key setup facts**:
- Required Debian packages: `curl`, `git`, `jq`, `libicu-dev` (runner dependency).
- Runner is installed by downloading the runner tarball from GitHub and running `./config.sh`.
- `./svc.sh install` registers it as a systemd service (`actions.runner.<org>-<repo>.<name>.service`).
- Runner MUST run as a dedicated non-root user (e.g., `github-runner`).
- The runner user MUST be added to the `docker` group to invoke Docker without `sudo`.
- Label the runner (e.g., `self-hosted,linux,eye-budget`) and reference that label in the workflow.

**Home-lab pitfalls to avoid**:
- Runner binary version must be kept updated (GitHub enforces a maximum age).
- Disk space must be monitored — old Docker images accumulate; a periodic `docker image prune` cron is advisable.
- Workflow `timeout-minutes` should be set (recommend 15 min) to prevent stuck jobs from blocking the queue indefinitely.

---

## 2. Next.js Dockerfile (Multi-stage + Standalone)

**Decision**: Multi-stage Dockerfile with `output: 'standalone'` enabled in `next.config.mjs`, using `node:20-slim` as the production base image.

**Rationale**: Standalone output traces only the files actually used and produces a self-contained `server.js` — no full `node_modules` needed at runtime. This reduces the production image from ~500MB+ to ~120–150MB. `node:20-slim` (glibc) is preferred over `node:20-alpine` (musl libc) for stability with npm native extensions.

**Alternatives considered**:
- `node:20-alpine` — 30% smaller but musl libc causes compatibility issues with some native packages. Not worth the risk for this project.
- No standalone mode — image would require full `node_modules`, bloating image size significantly.

**Critical standalone gotchas**:
- `public/` and `.next/static/` are NOT auto-copied into `.next/standalone` — they must be explicitly `COPY`-ed in the Dockerfile.
- `NEXT_PUBLIC_*` variables are baked into the JS bundle at build time and cannot be changed at runtime without rebuilding the image.
- The production entry point is `node server.js`, not `next start`.

**Recommended Dockerfile structure**:
```dockerfile
# Stage 1: deps
FROM node:20-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: builder
FROM node:20-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

# Stage 3: runner
FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
CMD ["node", "server.js"]
```

**Health check**: A lightweight `GET /api/health` endpoint returning `{ status: 'ok' }` is added to the Next.js app. The Docker `HEALTHCHECK` instruction polls it.

---

## 3. GitHub Actions Concurrency & Deployment Pattern

### Concurrency control

**Decision**: Use `concurrency` with `cancel-in-progress: false` and a static group name scoped to the deployment target.

**Rationale**: `cancel-in-progress: false` queues new runs instead of cancelling them, ensuring every push to master is eventually deployed in order. A static group name (e.g., `deploy-eye-budget-production`) ensures only one deployment runs at a time regardless of who triggered it.

```yaml
concurrency:
  group: deploy-eye-budget-production
  cancel-in-progress: false
```

### Deployment pattern (runner = server, same machine)

**Decision**: Build the image on the runner, then manage containers via the local Docker daemon directly. No SSH, no registry.

**Rationale**: When runner and server are the same machine, the Docker socket is local. `docker build`, `docker stop`, and `docker run` work directly — no image transfer overhead.

**Safe rollback pattern**:
1. Before replacing the container, tag the current image as `eye-budget-frontend:previous`.
2. Deploy the new image as `eye-budget-frontend:latest`.
3. Run health check (`curl http://localhost:3000/api/health`).
4. If health check fails: stop new container, start `eye-budget-frontend:previous`, fail the workflow with a clear error.

**Zero-downtime note**: For a home-lab / single-user scenario, the brief gap between `docker stop` and `docker run` (1–3 seconds) is acceptable. True zero-downtime (e.g., nginx upstream swap) is out of scope.

**Container run flags**:
- `--restart unless-stopped` — container auto-starts on server reboot.
- `-p 3000:3000` — port binding per spec.
- `--name eye-budget-frontend` — stable name for `docker stop`/`docker rm` idempotency.
