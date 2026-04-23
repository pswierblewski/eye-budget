# Quickstart: Semantic Versioning Display

## How to bump versions

### Frontend version
Edit `frontend/package.json`:
```json
{
  "version": "1.1.0"
}
```
Rebuild and redeploy. The new version is baked in at build time.

### Backend version
Edit `backend/src/version.py`:
```python
VERSION = "1.1.0"
```
Redeploy. The new version is returned by `GET /version` immediately.

---

## Verify in the UI

Open the app and check the bottom of the left sidebar. You will see:
```
Frontend: v1.0.0
Backend: v1.0.0
```

---

## Testing the fallback

Stop the backend and reload the page. The sidebar will show:
```
Frontend: v1.0.0
Backend: nieznana
```

---

## Running tests

```bash
# Backend — version endpoint integration test
cd backend && python -m pytest tests/integration/test_version.py -v

# Frontend — TypeScript check
cd frontend && npx tsc --noEmit

# Frontend — lint
cd frontend && npm run lint
```
