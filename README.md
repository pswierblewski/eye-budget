# Eye Budget

Receipt OCR pipeline — scans receipts, extracts transactions via OpenAI, and stores them for review.

## Stack

| Service | Role | Port |
|---|---|---|
| FastAPI (backend) | REST API | 8080 |
| Next.js (frontend) | UI | 3000 |
| Celery worker | Background task processing | — |
| Redis | Celery broker + result backend | 6379 |
| Soketi | Self-hosted WebSocket server (Pusher-compatible) | 6001 |
| PostgreSQL | Main database (external — 192.168.1.184) | 5432 |
| MinIO | Image object storage (external — 192.168.1.184) | 9000 |

---

## Setup

### 1. Create your `.env` file

```bash
cp .env.example .env
```

Fill in the required values (OpenAI key, Postgres credentials, MinIO credentials). Point `POSTGRESQL_HOST` and `MINIO_ENDPOINT` at `192.168.1.184` — PostgreSQL and MinIO are **not** managed by docker-compose. The only thing you **must** set beyond external service credentials is `OPENAI_API_KEY`.

The `NEXT_PUBLIC_*` vars need to be in the frontend's env as well. For local dev, copy the same file:

```bash
cp .env frontend/.env.local
```

### 2. Start all services

```bash
docker compose up --build
```

This starts: redis, soketi, the FastAPI backend, the Celery worker, and the Next.js frontend. PostgreSQL and MinIO are expected to be running on `192.168.1.184`.

To run in the background:

```bash
docker compose up --build -d
```

### 3. Run database migrations

On first run (or after pulling new migrations):

```bash
docker compose exec backend yoyo apply --database postgresql://$POSTGRESQL_USER:$POSTGRESQL_PASSWORD@192.168.1.184/$POSTGRESQL_DB ./migrations
```

Or with hardcoded credentials:

```bash
docker compose exec backend yoyo apply --database postgresql://eyebudget:eyebudget@192.168.1.184/eyebudget ./migrations
```

---

## Access

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API docs | http://localhost:8080/docs |
| MinIO console | http://192.168.1.184:9001 |

---

## Development (without Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

To activate the venv in subsequent sessions (without recreating it):

```bash
source backend/venv/bin/activate
```

Deactivate when done:

```bash
deactivate
```

Start the API server:

```bash
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

Start the Celery worker (separate terminal):

```bash
celery -A src.celery_app worker --loglevel=info
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Required local services

You still need Redis and Soketi running locally. PostgreSQL and MinIO are on `192.168.1.184` and accessed directly via your `.env` credentials. Start just the local services:

```bash
docker compose up redis soketi
```

---

## How processing works

- **Process receipts** (`POST /receipts/process`) — picks up images from the `input/` directory, runs OCR via OpenAI, normalises vendors and products, and saves results for review. Returns a `task_id` immediately (HTTP 202).
- **Run evaluation** (`POST /receipts/evaluate`) — runs OCR on all ground truth entries and scores accuracy. Returns a `task_id` immediately (HTTP 202).

Both long-running operations are dispatched to the **Celery worker**. The frontend subscribes to **Soketi** (WebSocket) and shows a live per-receipt progress bar. No polling, no timeouts.

Task status can also be checked via:

```
GET /tasks/{task_id}
```

---

## Stopping

```bash
docker compose down
```

To also remove persistent volumes (Redis data):

```bash
docker compose down -v
```

