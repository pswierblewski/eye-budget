# eye-budget Frontend — AI Agent README

## TL;DR — Highest-Priority Rules

1. **Pages are `"use client"`** — they use React Query, not React Server Components.
2. **API route handlers are thin proxies** — one `proxyGet`/`proxyPost` call, no business logic.
3. **All API calls go through `lib/api.ts`** — never `fetch` the backend directly from a component.
4. **All types come from Zod** — `z.infer<typeof Schema>` in `lib/types.ts`, no manual interfaces.
5. **Check `components/ui/` before creating UI elements** — the design system already has Button, Input, Modal, Badge, etc.
6. **Tailwind CSS only** — use `clsx` for conditional classes, never `tailwind-merge` or inline `style={{}}`.
7. **UI strings are in Polish** — do not introduce English copy.
8. **No form libraries** — controlled inputs with `useState`.
9. **`@/*` path alias** for all imports — configured in `tsconfig.json`.
10. **Invalidate queries after mutations** — always call `queryClient.invalidateQueries()` on success.

Full rules: `.cursor/rules/frontend/` (10–13 series).

## Stack

| | |
|---|---|
| Framework | Next.js 14, App Router |
| Language | TypeScript (strict) |
| Styling | Tailwind CSS v3 + Radix UI primitives + `clsx` |
| Data fetching | @tanstack/react-query v5 |
| Validation | Zod v3 |
| Icons | lucide-react |
| Charts | recharts |
| Real-time | Pusher / Soketi via `lib/pusher.ts` |
| Package manager | npm |

## Directory Layout

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout: QueryProvider + Sidebar
│   ├── page.tsx                # Unified transactions list (main page)
│   ├── bank-transactions/      # Bank transaction list + detail pages
│   ├── cash-transactions/      # Cash transaction list page
│   ├── receipts/               # Receipt list + detail pages
│   ├── evaluations/            # Evaluation list + detail pages
│   ├── ground-truth/           # Ground truth list + detail pages
│   └── api/                    # Next.js Route Handlers (thin proxies to backend)
├── components/
│   ├── ui/                     # Design-system primitives (see index.ts)
│   └── ...                     # Feature-level components
└── lib/
    ├── api.ts                  # Typed API client
    ├── types.ts                # Zod schemas + inferred TypeScript types
    ├── proxy.ts                # Server-side proxy helpers
    ├── pusher.ts               # Pusher/Soketi real-time client
    ├── utils.ts                # Date helpers
    └── sourceConfig.ts
```

## Run

```bash
npm run dev     # http://localhost:3000
npm run build
npm run lint
```

Backend is expected at `http://localhost:8080` (or `BACKEND_URL` env var).

## API Call Flow

```
Page component ("use client")
  └─ useQuery/useMutation (React Query)
       └─ lib/api.ts function (e.g. listBankTransactions)
            └─ apiFetch<T>(url, zodSchema)
                 └─ fetch /api/bank-transactions
                      └─ app/api/bank-transactions/route.ts
                           └─ proxyGet(req) from lib/proxy.ts
                                └─ FastAPI backend
```

## Design Tokens (tailwind.config.ts)

- Accent: `bg-accent` / `text-accent` → `#635bff`
- Sidebar background: `bg-sidebar` → `#f6f9fc`
- Status colors: `status.pending`, `status.processing`, `status.done`, `status.failed`, `status.to_confirm`
- Font: Inter (via `fontFamily.sans`)

## Canonical References

- `frontend/components/ui/Button.tsx` — variant + size pattern
- `frontend/components/ui/Input.tsx` — inputSize pattern
- `frontend/components/ui/Modal.tsx` — controlled modal, Escape key handler
- `frontend/components/ui/index.ts` — full list of design-system exports
- `frontend/lib/api.ts` — `apiFetch`, all domain API functions
- `frontend/lib/types.ts` — Zod schemas + `paginatedSchema` helper
- `frontend/lib/proxy.ts` — `proxyGet` / `proxyPost` / etc.
- `frontend/app/layout.tsx` — root layout with providers
- `frontend/app/bank-transactions/page.tsx` — representative list page with Pusher
- `frontend/app/bank-transactions/[id]/page.tsx` — representative detail page with mutations
- `frontend/app/receipts/[id]/page.tsx` — complex multi-field edit form
- `frontend/tailwind.config.ts` — all design tokens
