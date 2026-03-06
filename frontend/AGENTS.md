# eye-budget Frontend — AI Agent README

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
│       ├── bank-transactions/
│       ├── cash-transactions/
│       ├── receipts/
│       ├── categories/
│       ├── products/
│       ├── vendors/
│       ├── tags/
│       ├── transactions/
│       └── evaluations/
├── components/
│   ├── ui/                     # Design-system primitives (see index.ts)
│   ├── AnalyticsPanel.tsx
│   ├── CategoryDropdown.tsx
│   ├── DataTable.tsx
│   ├── QueryProvider.tsx
│   ├── Sidebar.tsx
│   └── ...
└── lib/
    ├── api.ts                  # Typed API client — all client-side data calls go here
    ├── types.ts                # Zod schemas + inferred TypeScript types
    ├── proxy.ts                # Server-side proxy helpers (proxyGet, proxyPost, …)
    ├── pusher.ts               # Pusher/Soketi real-time client
    ├── utils.ts                # Date helpers (isoToDisplay, displayToIso)
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

## Key Rules (summary — full rules in .cursor/rules/)

- **Pages are `"use client"`** and use React Query; they are NOT React Server Components.
- **API route handlers** are thin proxies — one `proxyGet`/`proxyPost`/etc. call, nothing more.
- **All API calls** go through `lib/api.ts` — never `fetch` the backend directly from a component.
- **All types** come from `z.infer<typeof Schema>` in `lib/types.ts` — no manual interfaces.
- **UI strings are in Polish.**

## Design Tokens (tailwind.config.ts)

- Accent: `bg-accent` / `text-accent` → `#635bff`
- Sidebar background: `bg-sidebar` → `#f6f9fc`
- Status colors: `status.pending`, `status.processing`, `status.done`, `status.failed`, `status.to_confirm`
- Font: Inter (via `fontFamily.sans`)
