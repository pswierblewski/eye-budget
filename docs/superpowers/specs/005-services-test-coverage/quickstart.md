# Quickstart: Running Service Tests

**Feature**: 005-services-test-coverage  
**Updated**: 2026-03-30

---

## Prerequisites

```bash
source venv/bin/activate
cd backend
pip install -r requirements-test.txt   # installs pytest-asyncio>=0.23 (new)
```

---

## Run all unit tests (including new service tests)

```bash
cd backend
python -m pytest -m unit
```

Expected output: all tests pass, coverage report for `src/services/` printed, suite fails if coverage < 80%.

---

## Run a specific service test group

```bash
# Pure-logic services (no mocks needed)
python -m pytest tests/unit/test_services_pure.py -v

# LLM services (mocked OpenAI client)
python -m pytest tests/unit/test_services_llm.py -v

# Infrastructure services (mocked MinIO, Pusher)
python -m pytest tests/unit/test_services_infra.py -v

# Domain / calculation services
python -m pytest tests/unit/test_services_domain.py -v

# Image-processing services
python -m pytest tests/unit/test_services_image.py -v
```

---

## Run with coverage report only (no fail-under gate)

```bash
python -m pytest tests/unit/ --cov=src/services --cov-report=term-missing --no-cov-on-fail
```

---

## Run existing integration tests (unchanged)

```bash
python -m pytest -m integration
```

Integration tests require Docker (PostgreSQL + MinIO via testcontainers).

---

## Check coverage for a single service file

```bash
python -m pytest tests/unit/test_services_llm.py \
  --cov=src/services/ocr \
  --cov-report=term-missing
```
