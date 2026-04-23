# Tasks: Goal Priority Tooltip

**Input**: Design documents from `/specs/002-goal-priority-tooltip/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅

**Organization**: Single user story (P1) — all tasks belong to one phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: User Story 1 — Odczytanie wyjaśnienia priorytetu

---

## Phase 3: User Story 1 — Odczytanie wyjaśnienia priorytetu (Priority: P1) 🎯 MVP

**Goal**: Ikonka ⓘ obok pola "Priorytet" w `GoalForm` z tooltipem wyjaśniającym zasadę priorytetu.

**Independent Test**: Otwórz formularz celu finansowego → najedź kursorem na ikonkę ⓘ obok "Priorytet" → tooltip z wyjaśnieniem pojawia się natychmiast. Sprawdź: tooltip znika po odjechaniu; jest czytelny na mobile (tap).

### Implementacja User Story 1

- [x] T001 [P] [US1] Utwórz komponent `Tooltip` w `frontend/components/ui/Tooltip.tsx` — wrapper na `@radix-ui/react-tooltip` z propsami `content: ReactNode`, `children: ReactNode`, `side?: "top"|"right"|"bottom"|"left"` (domyślnie `"top"`), `delayDuration?: number` (domyślnie 300); stylowanie: `bg-gray-900 text-white text-xs rounded-lg px-3 py-2 shadow-lg`; portal + arrow `fill-gray-900`; `Provider` wrappuje `Root`
- [ ] T002 [P] [US1] ⚠️ BLOCKED — brak test frameworka (jest/vitest + @testing-library/react nie skonfigurowane). Napisz test jednostkowy dla `Tooltip` w `frontend/components/ui/__tests__/Tooltip.test.tsx` po skonfigurowaniu test runnera — sprawdź: trigger renderuje się; `content` pojawia się po symulacji hover/focus; komponent przyjmuje poprawne typy TypeScript (constitution II: nowe komponenty z conditional rendering wymagają testów)
- [x] T003 [US1] Dodaj eksport `Tooltip` do `frontend/components/ui/index.ts` — wstaw linię `export { Tooltip } from "./Tooltip";` (zależy od T001)
- [x] T004 [US1] Zaktualizuj `frontend/components/budget/GoalForm.tsx` — dodaj import `{ Tooltip }` z `@/components/ui` i `{ Info }` z `lucide-react`; zmień etykietę "Priorytet" (linia 90) na `<label className="flex items-center gap-1 text-xs font-medium text-gray-600 mb-1">` z tekstem "Priorytet" oraz `<Tooltip content="Niższy numer oznacza wyższy priorytet. Priorytet 1 to cel najważniejszy, wyższe liczby oznaczają mniejsze znaczenie (np. 5 = cel drugorzędny)."><span tabIndex={0} className="inline-flex cursor-help focus:outline-none"><Info className="w-3.5 h-3.5 text-gray-400" /></span></Tooltip>` (zależy od T001, T003)

**Checkpoint**: Formularz celu finansowego działa poprawnie z tooltip na polu Priorytet — gotowe do testu manualnego wg quickstart.md

---

## Phase N: Polish & Weryfikacja

**Purpose**: Walidacja jakości kodu

- [x] T005 Uruchom `cd frontend && npx tsc --noEmit` — zero błędów TypeScript
- [x] T006 [P] Uruchom `cd frontend && npm run lint` — zero błędów ESLint
- [x] T007 [P] Uruchom `cd frontend && npm run build` — zero błędów, brak regresji bundle

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 3 (US1)**: Może startować od razu — brak blokerów infrastrukturalnych
- **Phase N (Polish)**: Zależy od ukończenia Phase 3

### User Story Dependencies

- **T001 i T002**: Mogą być tworzone równolegle (różne pliki)
- **T003**: Zależy od T001 (plik Tooltip.tsx musi istnieć)
- **T004**: Zależy od T001 i T003 (komponent + eksport muszą być gotowe)
- **T005, T006, T007**: Zależą od T001–T004 (cały kod musi być na miejscu)

### Parallel Opportunities

```
Równolegle:  T001 (Tooltip.tsx) + T002 (Tooltip.test.tsx)
Następnie:   T003 (index.ts export)        ← wymaga T001
Następnie:   T004 (GoalForm.tsx update)    ← wymaga T001 + T003
Następnie:   T005 + T006 + T007            ← wszystkie równolegle
```

---

## Implementation Strategy

### MVP (jedyna historia = cały zakres)

1. T001 + T002 równolegle
2. T003 → T004
3. T005 + T006 + T007
4. Test manualny wg quickstart.md

---

## Notes

- Żadnych zmian backendowych — feature jest 100% frontendowy
- Żadnych nowych zależności npm — `@radix-ui/react-tooltip` już zainstalowany
- Żadnych migracji DB
- Constitution II wymaga T002 (test) przed mergem — nie pomijać
- `[P]` = różne pliki, brak wzajemnych zależności
