# Implementation Plan: Goal Priority Tooltip

**Branch**: `002-goal-priority-tooltip` | **Date**: 2026-03-17 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-goal-priority-tooltip/spec.md`

## Summary

Dodanie ikonki informacyjnej (ⓘ) obok etykiety pola "Priorytet" w formularzu celów finansowych (`GoalForm`). Ikonka po najechaniu kursorem pokazuje tooltip z wyjaśnieniem, że niższy numer priorytetu oznacza wyższy priorytet celu. Zmiana jest w 100% frontendowa: nowy komponent `Tooltip` w design system + aktualizacja `GoalForm`.

## Technical Context

**Language/Version**: TypeScript 5 / Node 20
**Primary Dependencies**: Next.js 14 App Router, React 18, `@radix-ui/react-tooltip` v1.1.2 (already installed), `lucide-react`
**Storage**: N/A — no DB changes
**Testing**: `npx tsc --noEmit` + `npm run lint` + `npm run build`
**Target Platform**: Browser (desktop + mobile/touch)
**Project Type**: Web application (frontend-only change)
**Performance Goals**: Tooltip renders instantly (CSS transition); no async operations
**Constraints**: No new npm packages; no backend changes; must pass `npm run build` without bundle regressions
**Scale/Scope**: 1 new UI component, 2 modified files

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Code Quality | ✅ PASS | Single-responsibility `Tooltip` wrapper; strict TypeScript; no `any`; no hardcoded values |
| II. Testing | ✅ PASS | Unit test for `Tooltip` component required (conditional rendering); `GoalForm` change is trivial label update — no new state logic |
| III. UX Consistency | ✅ PASS | Polish strings; uses `lucide-react` (`Info`); new primitive added to `components/ui/` per constitution |
| IV. Performance | ✅ PASS | Pure CSS tooltip; zero network calls; no bundle regression expected |
| V. Frontend Architecture | ✅ PASS | Tailwind only; no inline `style={{}}`; `clsx` for conditionals; `@radix-ui/react-tooltip` already installed |
| VI. Backend Conventions | ✅ N/A | No backend changes |
| API Contract Integrity | ✅ N/A | No API changes |

**Gate result**: All gates pass. No violations to justify.

## Project Structure

### Documentation (this feature)

```text
specs/002-goal-priority-tooltip/
├── plan.md              ← this file
├── research.md          ← Phase 0 output
├── quickstart.md        ← Phase 1 output
└── tasks.md             ← Phase 2 output (/speckit.tasks)
```

### Source Code (affected files only)

```text
frontend/
├── components/
│   ├── ui/
│   │   ├── Tooltip.tsx          ← NEW: reusable Tooltip primitive
│   │   └── index.ts             ← MODIFIED: add Tooltip export
│   └── budget/
│       └── GoalForm.tsx         ← MODIFIED: add Info icon + Tooltip to "Priorytet" label
```

No new directories. No backend files. No migration files.

**Structure Decision**: Web application, Option 2 — only frontend/ is touched.

## Phase 0: Research

**Status**: Complete → [research.md](research.md)

Key decisions:
- `@radix-ui/react-tooltip` (already installed) — accessible hover + touch support, auto collision detection
- `Info` from `lucide-react` — only permitted icon library per constitution
- New `Tooltip` component in `components/ui/` — reusable, consistent with design system

## Phase 1: Design & Contracts

**Status**: Complete — frontend-only feature, no data model or API contracts needed.

- [data-model.md]: N/A — no DB entities
- [contracts/]: N/A — no API changes
- [quickstart.md](quickstart.md): ✅ Complete

### Component Design: `Tooltip`

```tsx
// frontend/components/ui/Tooltip.tsx
"use client";

import * as RadixTooltip from "@radix-ui/react-tooltip";
import { ReactNode } from "react";

interface TooltipProps {
  content: ReactNode;
  children: ReactNode;
  side?: "top" | "right" | "bottom" | "left";
  delayDuration?: number;
}

export function Tooltip({ content, children, side = "top", delayDuration = 300 }: TooltipProps) {
  return (
    <RadixTooltip.Provider delayDuration={delayDuration}>
      <RadixTooltip.Root>
        <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
        <RadixTooltip.Portal>
          <RadixTooltip.Content
            side={side}
            sideOffset={4}
            className="z-50 max-w-xs rounded-lg bg-gray-900 px-3 py-2 text-xs text-white shadow-lg animate-in fade-in-0 zoom-in-95"
          >
            {content}
            <RadixTooltip.Arrow className="fill-gray-900" />
          </RadixTooltip.Content>
        </RadixTooltip.Portal>
      </RadixTooltip.Root>
    </RadixTooltip.Provider>
  );
}
```

### GoalForm change (Priorytet label, line 90)

```tsx
// Before:
<label className="block text-xs font-medium text-gray-600 mb-1">Priorytet</label>

// After:
<label className="flex items-center gap-1 text-xs font-medium text-gray-600 mb-1">
  Priorytet
  <Tooltip content="Niższy numer oznacza wyższy priorytet. Priorytet 1 to cel najważniejszy, wyższe liczby oznaczają mniejsze znaczenie (np. 5 = cel drugorzędny).">
    <span tabIndex={0} className="inline-flex cursor-help focus:outline-none">
      <Info className="w-3.5 h-3.5 text-gray-400" />
    </span>
  </Tooltip>
</label>
```

Note: `<span tabIndex={0}>` wraps the icon to ensure keyboard accessibility (Radix Tooltip trigger responds to `focus-visible`).

## Implementation Checklist

- [ ] Create `frontend/components/ui/Tooltip.tsx`
- [ ] Export `Tooltip` from `frontend/components/ui/index.ts`
- [ ] Update `GoalForm.tsx`: import `Tooltip`, `Info`; update Priorytet label
- [ ] Write unit test for `Tooltip` component
- [ ] `npx tsc --noEmit` — zero errors
- [ ] `npm run lint` — zero errors
- [ ] `npm run build` — zero errors
