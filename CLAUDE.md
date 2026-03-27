# eye-budget Development Guidelines

Last updated: 2026-03-25

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
- 004-cicd-local-deploy: CI/CD pipeline spec + tasks complete, implementation in progress
- 003-backend-app-tests: Python test suite (unit + integration), DI refactor, AAA comments
- 002-goal-priority-tooltip: goal priority tooltip with Radix UI
- 001-budget-analysis: core budget analysis feature

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
