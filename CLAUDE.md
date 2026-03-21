# eye-budget Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-03-21

## Active Technologies
- Python 3.11.7 (venv at project root `venv/`) + FastAPI, psycopg2-binary, pydantic v2, yoyo-migrations 9.0.0, minio client (003-backend-app-tests)
- PostgreSQL (psycopg2-binary), MinIO (S3-compatible) (003-backend-app-tests)
- GitHub Actions YAML, Dockerfile (Node 20 / node:20-slim), TypeScript 5 / Node 20 (Next.js 14) + GitHub Actions self-hosted runner, Docker (already on server), Node 20 (004-cicd-local-deploy)

- TypeScript 5 / Node 20 + Next.js 14 App Router, React 18, `@radix-ui/react-tooltip` v1.1.2 (already installed), `lucide-react` (002-goal-priority-tooltip)

## Project Structure

```text
src/
tests/
```

## Commands

npm test && npm run lint

## Code Style

TypeScript 5 / Node 20: Follow standard conventions

## Recent Changes
- 004-cicd-local-deploy: Added GitHub Actions YAML, Dockerfile (Node 20 / node:20-slim), TypeScript 5 / Node 20 (Next.js 14) + GitHub Actions self-hosted runner, Docker (already on server), Node 20
- 003-backend-app-tests: Added Python 3.11.7 (venv at project root `venv/`) + FastAPI, psycopg2-binary, pydantic v2, yoyo-migrations 9.0.0, minio client

- 002-goal-priority-tooltip: Added TypeScript 5 / Node 20 + Next.js 14 App Router, React 18, `@radix-ui/react-tooltip` v1.1.2 (already installed), `lucide-react`

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
