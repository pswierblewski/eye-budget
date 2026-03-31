# Data Model: Semantic Versioning Display

## Entities

### VersionResponse (Backend — Pydantic model in `backend/src/data.py`)

Represents the version information returned by the backend `/version` endpoint.

| Field     | Type   | Constraints              | Description                        |
|-----------|--------|--------------------------|------------------------------------|
| version   | str    | required, semver pattern | Backend version, e.g. `"1.0.0"`   |
| component | str    | required, literal        | Always `"backend"`                 |

**Validation**: No DB interaction. Value sourced from `backend/src/version.py`.

---

### VersionInfoSchema (Frontend — Zod schema in `frontend/lib/types.ts`)

Mirrors `VersionResponse` for runtime validation of the API response.

```typescript
export const VersionInfoSchema = z.object({
  version: z.string(),
  component: z.string(),
});
export type VersionInfo = z.infer<typeof VersionInfoSchema>;
```

---

## State Transitions

No state transitions — version is a static read-only value per deployment. The only lifecycle event is:

```
App startup → fetch /api/version → cache in React Query (staleTime: Infinity) → display in Sidebar
```

On error or timeout: React Query error state → Sidebar shows `"nieznana"` as fallback.

---

## Version Sources Summary

| Component | Authoritative Source               | Exposure Mechanism                        |
|-----------|------------------------------------|-------------------------------------------|
| Frontend  | `frontend/package.json` → `version` | `NEXT_PUBLIC_FRONTEND_VERSION` via `next.config.mjs` |
| Backend   | `backend/src/version.py` → `VERSION` | Returned by `GET /version` endpoint      |
