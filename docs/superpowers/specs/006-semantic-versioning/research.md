# Research: Semantic Versioning Display

## 1. Frontend Version — Single Source of Truth

**Decision**: Use `frontend/package.json` `version` field as the authoritative source. Expose it at build time via `next.config.mjs` using `env.NEXT_PUBLIC_FRONTEND_VERSION`.

**Rationale**: `package.json` already has a `version` field (currently `"0.1.0"`). Bumping the frontend version means editing one field in one file. Exposing it via `env` in `next.config.mjs` (by reading `package.json` at build time) bakes the value into the Next.js bundle — no runtime overhead and no duplication.

**Alternatives considered**:
- `frontend/lib/version.ts` with a hardcoded `export const VERSION = "1.0.0"` — rejected: creates a second source of truth alongside `package.json`.
- Runtime `fetch` to a `/frontend-version` endpoint — rejected: needlessly complex for a static build-time value.

**Implementation**:
```js
// next.config.mjs
import pkg from './package.json' assert { type: 'json' };
const nextConfig = {
  output: 'standalone',
  env: { NEXT_PUBLIC_FRONTEND_VERSION: pkg.version },
};
export default nextConfig;
```

---

## 2. Backend Version — Single Source of Truth

**Decision**: New file `backend/src/version.py` containing `VERSION = "1.0.0"`. Imported by `main.py` and returned by the `/version` endpoint.

**Rationale**: Mirrors the Python convention of a `__version__` or `version.py` module. Single location to edit when bumping the backend version. No external package management or build tooling required.

**Alternatives considered**:
- Reading from `pyproject.toml` / `setup.py` — rejected: project does not use these files; adds unnecessary dependency on packaging metadata.
- Hardcoding version string directly in `main.py` — rejected: version would be buried in route handler, not a clearly named source of truth.

---

## 3. Backend Endpoint Design

**Decision**: `GET /version` — public (no authentication), returns `VersionResponse` Pydantic model. Added to `backend/src/main.py` under a `# --- System ---` comment section.

**Rationale**: The constitution mandates all routes live in `main.py` with `response_model=` declared. No `App()` lifecycle needed — no DB access, pure in-memory response. Public endpoint by clarified requirement (Q2 answer).

**Performance**: Well within the 200ms p95 requirement — response is a constant in-memory string lookup.

---

## 4. Frontend Fetch Strategy

**Decision**: `useQuery({ queryKey: ["version"], queryFn: getVersionInfo, staleTime: Infinity, gcTime: Infinity })` in `Sidebar.tsx`.

**Rationale**: React Query with `staleTime: Infinity` fetches once at mount and never re-fetches. Since the Sidebar is mounted once per app session and backend version only changes on deployment (page reload), this matches the "fetch once at startup, cache for session" clarification.

**Fallback**: When the query is in loading or error state, display `"..."` (loading) or `"nieznana"` (error), per FR-007.

---

## 5. Version Display in Sidebar

**Decision**: Add a `<footer>` element inside the `<aside>` in `Sidebar.tsx`, below the `<nav>`. Display two lines: `Frontend: vX.X.X` and `Backend: vX.X.X`.

**Rationale**: The `<aside>` currently uses `flex flex-col` with `<nav className="flex-1 ...">`. Adding a footer div after nav naturally pushes it to the bottom without layout changes. Styling uses `text-gray-400 text-[10px]` matching the existing "Narzędzia" label style for visual hierarchy consistency.

**Polish labels per constitution (Principle III — all user-facing strings in Polish)**:
- Frontend line: `Frontend: vX.X.X` (technical term "Frontend" acceptable as-is in Polish dev context)
- Backend line: `Backend: vX.X.X`
- Loading: `ładowanie...`
- Fallback error: `nieznana`
