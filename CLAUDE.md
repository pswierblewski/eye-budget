# eye-budget Development Guidelines

Last updated: 2026-04-01

## Stack

**Frontend** (`frontend/`): TypeScript 5 / Node 20, Next.js 14 App Router, React 18, Tailwind CSS, `@radix-ui/react-tooltip` v1.1.2, `lucide-react`

**Backend** (`backend/`): Python 3.11.7, FastAPI, psycopg2-binary, pydantic v2, yoyo-migrations 9.0.0, MinIO client, Celery[redis], PaddleOCR (PaddlePaddle ≥3.0), OpenAI SDK, Pusher

**Infrastructure**: PostgreSQL, MinIO (S3-compatible), Redis, Docker / Docker Compose

**CI/CD** (in progress — `004-cicd-local-deploy`): GitHub Actions self-hosted runner, deploys Next.js Docker image to Debian server at `192.168.1.184:3000`

## Project Structure

```text
frontend/
  app/            # Next.js App Router pages & API routes
  components/
  lib/
backend/
  src/            # FastAPI app (main.py, celery_app.py, repositories/, services/, tasks/)
  tests/          # unit/ and integration/ suites, conftest.py
  migrations/     # yoyo SQL migrations
  requirements.txt
  requirements-test.txt
specs/            # per-feature design artifacts (spec.md, plan.md, tasks.md, ...)
venv/             # Python virtualenv (project root)
docker-compose.yml
```

## Commands

```bash
# Frontend
cd frontend && npm test && npm run lint

# Backend tests
cd backend && python -m pytest

# Python venv
source venv/bin/activate
```

## Code Style

- TypeScript: follow standard Next.js / React conventions
- Python: follow FastAPI / pydantic v2 conventions; tests use AAA (Arrange / Act / Assert) comment structure

## Feature Workflow

Features follow the speckit workflow: `specs/<NNN-feature-name>/` contains `spec.md`, `plan.md`, `tasks.md`, and supplementary artifacts. One branch per feature; PR to `master`.

## Recent Changes
- 008-fix-category-id-ambiguity: Added Python 3.11.7 + FastAPI, psycopg2-binary, pydantic v2, pytest ≥ 8.0, pytest-mock ≥ 3.14
- 007-fix-paddle-pickling: Added Python 3.11.7 + PaddleOCR ≥ 2.10, concurrent.futures.ProcessPoolExecutor, pytest ≥ 8.0, pytest-mock ≥ 3.14
- 006-semantic-versioning: Added TypeScript 5 / Node 20 (frontend); Python 3.11.7 (backend) + Next.js 14, React 18, @tanstack/react-query v5 (frontend); FastAPI, Pydantic v2 (backend)

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

## Active Technologies
- Python 3.11.7 + FastAPI, psycopg2-binary, pydantic v2, pytest ≥ 8.0, pytest-mock ≥ 3.14 (008-fix-category-id-ambiguity)
- PostgreSQL (no schema changes) (008-fix-category-id-ambiguity)
