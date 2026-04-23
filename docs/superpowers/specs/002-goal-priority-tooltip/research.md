# Research: Goal Priority Tooltip

**Branch**: `002-goal-priority-tooltip` | **Date**: 2026-03-17

---

## Decision 1: Tooltip implementation mechanism

**Decision**: Use `@radix-ui/react-tooltip` (already installed, v1.1.2).

**Rationale**:
- Already a project dependency — no new packages needed.
- Provides accessible hover + focus-visible support out of the box (ARIA `role="tooltip"`, keyboard `Escape` to dismiss).
- Handles collision detection (auto-flips when near viewport edge) — covers the edge case from the spec.
- On mobile/touch: Radix Tooltip opens on long-press and can be toggled via tap on the trigger — acceptable for the spec requirement.

**Alternatives considered**:
- Native HTML `title` attribute — dismissed: no styling control, no mobile support, fails FR-005 (tap toggle).
- `@radix-ui/react-popover` — overkill for read-only tooltip; Tooltip primitive is the right semantic choice.
- Custom CSS hover state — not accessible (no keyboard support).

---

## Decision 2: Icon

**Decision**: `Info` from `lucide-react`.

**Rationale**: Constitution V mandates `lucide-react` as the only icon library. `Info` maps directly to "i in a circle" — exact visual spec requirement.

**Alternatives considered**: None — constitution prohibits other icon libraries.

---

## Decision 3: Tooltip component placement

**Decision**: Create a new `Tooltip` component in `frontend/components/ui/Tooltip.tsx` and export it from `frontend/components/ui/index.ts`.

**Rationale**:
- Constitution III: "UI components MUST be sourced from the design-system primitives exported by `frontend/components/ui/index.ts`. New primitives MUST NOT be created without first confirming no equivalent exists."
- There is no `Tooltip` in `components/ui/` — creating one is correct per constitution.
- Reusable across the app for future tooltip needs.

**Alternatives considered**:
- Inline Radix Tooltip directly in `GoalForm.tsx` — violates the "no inline primitives" spirit of the design system.

---

## Decision 4: Tooltip trigger — icon only vs label+icon

**Decision**: Keep the label text ("Priorytet") unchanged; add the `Info` icon inline after the label text, wrapped in the Tooltip trigger.

**Rationale**: Least invasive change, preserves existing layout, matches spec ("obok pola priorytetu").

---

## Resolved unknowns

- No DB changes needed — priority_rank semantics are purely a UI concern.
- No API changes needed — tooltip content is static client-side text.
- No backend changes — feature is 100% frontend.
