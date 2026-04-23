# Quickstart: Goal Priority Tooltip

**Branch**: `002-goal-priority-tooltip` | **Date**: 2026-03-17

---

## What this feature adds

A new reusable `Tooltip` UI primitive and its first use in `GoalForm` — an info icon next to the "Priorytet" label that shows an explanatory tooltip on hover.

---

## New component: `Tooltip`

Thin wrapper around `@radix-ui/react-tooltip`. Use anywhere in the app to show contextual help text.

```tsx
import { Tooltip } from "@/components/ui";

<Tooltip content="Niższy numer = wyższy priorytet. Priorytet 1 to cel najważniejszy.">
  <Info className="w-3.5 h-3.5 text-gray-400 cursor-help" />
</Tooltip>
```

**Props**:
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `content` | `React.ReactNode` | required | Tooltip body |
| `children` | `React.ReactNode` | required | Trigger element |
| `side` | `"top" \| "right" \| "bottom" \| "left"` | `"top"` | Preferred placement |
| `delayDuration` | `number` | `300` | Hover delay in ms |

---

## Changed file

**`frontend/components/budget/GoalForm.tsx`** — the "Priorytet" label row gains an inline info icon:

```tsx
<label className="block text-xs font-medium text-gray-600 mb-1 flex items-center gap-1">
  Priorytet
  <Tooltip content="Niższy numer oznacza wyższy priorytet. Priorytet 1 to cel najważniejszy, wyższe liczby oznaczają mniejsze znaczenie (np. 5 = cel drugorzędny).">
    <Info className="w-3.5 h-3.5 text-gray-400 cursor-help" />
  </Tooltip>
</label>
```

---

## File map

```text
frontend/
├── components/
│   ├── ui/
│   │   ├── Tooltip.tsx          ← NEW
│   │   └── index.ts             ← add Tooltip export
│   └── budget/
│       └── GoalForm.tsx         ← add Info icon + Tooltip to Priorytet label
```

No backend changes. No migrations. No API changes.
