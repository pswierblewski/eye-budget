# Lista bankowa — przycisk „Zapisz kategorię” zawsze pod propozycją AI

**Date:** 2026-04-21  
**Status:** Draft (ready for review)  
**Suggested branch:** kontynuacja `feature/bank-tx-list-ai-category` lub krótki fix na gałęzi z tego PR

---

## Problem

W kolumnie „Kategoria” na `/bank-transactions`, gdy pokazywana jest propozycja AI + przycisk „Zapisz kategorię”, układ jest **niestabilny**: przy większej szerokości komórki przycisk bywa **z prawej** od nazwy i wyniku (jeden wiersz), przy mniejszej — **pod spodem**. Ma to być **zawsze pod spodem**.

---

## Scope

- **Tylko** blok listy: warunek `shouldShowAiCategoryProposal(t) && t.ai_top_candidate` w `frontend/app/bank-transactions/page.tsx`.
- **Bez zmian:** rozwinięty wiersz (expanded), strona szczegółu `/bank-transactions/[id]`, transakcje gotówkowe, logika API, Pusher, `shouldShowAiCategoryProposal`.

---

## Zachowanie docelowe (UI)

1. **Wiersz 1:** propozycja AI — **nazwa kategorii** + **wynik (pewność)** jak dotychczas wizualnie (małe szarości, `text-xs`), w poziomie w obrębie pierwszej linii; dopuszczalne `flex-wrap` **tylko** w tej linii, jeśli nazwa + liczba są bardzo długie.
2. **Wiersz 2:** przycisk **`Button` `variant="secondary"` `size="sm"`** — etykiety „Zapisz kategorię” / „Zapisywanie…”, **`stopPropagation`** na kliknięciu, wyłączenie przy `isPending` — bez zmian funkcjonalnie.
3. Kontener zewnętrzny: **układ pionowy** (`flex flex-col` + sensowny `gap`, np. `gap-1.5`) zamiast jednego poziomego rzędu z `flex-wrap` obejmującym przycisk.

---

## Opcje techniczne

| Opcja | Opis | Ocena |
|-------|------|--------|
| **A — `flex-col` + wewnętrzny rząd** | Zewnętrzny `div`: `flex flex-col gap-1.5`; wewnętrzny `div`: `flex flex-wrap items-center gap-1.5` tylko dla nazwy i wyniku; potomny `Button`. | **Rekomendowana** — minimalna zmiana, czytelny DOM |
| **B — CSS Grid** | `grid` z dwoma wierszami; pierwszy wiersz podrzędny flex dla tekstów. | Równoważne, niepotrzebnie cięższe |
| **C — Dwa bloki `block`** | Dwa `div` bez flex zewnętrznego; drugi z przyciskiem. | OK, ale `gap` jest wygodniejszy w `flex-col` |

**Rekomendacja:** **A**.

---

## Testy

- Brak zmian w `bankTxCategoryListUi` — testy Vitest dla reguł widoczności **bez zmian**.
- Weryfikacja: `npx tsc --noEmit`, `npm run lint`, opcjonalnie ręczny podgląd kilku szerokości kolumny.

---

## Self-review

- [x] Brak TBD.
- [x] Scope tylko lista bankowa — expanded/detail poza zakresem.
- [x] Zachowanie przycisku (mutation, stopPropagation) niezmienione.
