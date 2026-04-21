# Bank list — przycisk „Zapisz kategorię” zawsze pod AI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** W komórce „Kategoria” na `/bank-transactions` przycisk „Zapisz kategorię” jest zawsze w drugim wierszu pod linią nazwa + pewność.

**Architecture:** Zewnętrzny kontener `flex flex-col gap-1.5`; wewnętrzny `div` z `flex flex-wrap items-center gap-1.5` tylko dla tekstów; `Button` jako osobne dziecko.

**Tech Stack:** Next.js, Tailwind, istniejący `Button`.

**Spec:** `docs/superpowers/specs/2026-04-21-bank-tx-list-save-button-layout-design.md` (Approved)

---

## File map

| File | Change |
|------|--------|
| `frontend/app/bank-transactions/page.tsx` | Blok AI: zamiana jednego `flex-wrap` na `flex-col` + zagnieżdżony rząd dla nazwy i wyniku |

---

### Task 1: Układ komórki

**Files:**
- Modify: `frontend/app/bank-transactions/page.tsx` (accessor kolumny „Kategoria”, blok `shouldShowAiCategoryProposal`)

- [x] **Step 1:** Zastąp wrapper `className="flex max-w-[220px] flex-wrap items-center gap-1.5"` kontenerem `flex max-w-[220px] flex-col gap-1.5`.
- [x] **Step 2:** Owiń oba `span` (nazwa + wynik) w `<div className="flex flex-wrap items-center gap-1.5">`.
- [x] **Step 3:** Zostaw `Button` jako bezpośrednie dziecko zewnętrznego `flex-col` (po wewnętrznym `div`).
- [x] **Step 4:** `cd frontend && npx tsc --noEmit && npm run lint && npm run test:run`
- [x] **Step 5:** Commit poniżej (z wersją 1.2.1).

---

Plan self-review: jedno zadanie, zgodne ze specem; brak zmian w API ani helperach.
