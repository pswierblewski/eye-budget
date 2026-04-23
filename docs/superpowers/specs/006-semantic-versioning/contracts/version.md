# API Contract: GET /version

## Endpoint

`GET /version`

**Authentication**: None required (public endpoint)  
**Description**: Returns the current version of the backend component.

---

## Request

No request body or query parameters.

---

## Response — 200 OK

```json
{
  "version": "1.0.0",
  "component": "backend"
}
```

| Field     | Type   | Description                                      |
|-----------|--------|--------------------------------------------------|
| version   | string | Semantic version string (MAJOR.MINOR.PATCH)      |
| component | string | Always `"backend"` — identifies the responder    |

---

## Next.js Proxy Route

`GET /api/version` → proxies to `GET /version` on the FastAPI backend.

The Next.js route handler (`frontend/app/api/version/route.ts`) is a thin proxy using `proxyGet("/version")` from `lib/proxy.ts`. No transformation of the response.

---

## Error Handling

| Scenario              | HTTP Status | Frontend behaviour              |
|-----------------------|-------------|---------------------------------|
| Backend unreachable   | Network error | Query enters error state → sidebar shows `"nieznana"` |
| Unexpected response shape | Schema parse error | Zod parse fails → sidebar shows `"nieznana"` |

---

## All Layers (Constitution API Contract Integrity)

| Layer | Location | Change |
|-------|----------|--------|
| Route definition | `backend/src/main.py` | `GET /version` with `response_model=VersionResponse` |
| Pydantic model | `backend/src/data.py` | `VersionResponse` |
| Next.js proxy handler | `frontend/app/api/version/route.ts` | `proxyGet("/version")` |
| Typed client function | `frontend/lib/api.ts` | `getVersionInfo()` |
| Zod schema + type | `frontend/lib/types.ts` | `VersionInfoSchema`, `VersionInfo` |
