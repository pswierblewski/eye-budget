# Powiązane operacje — plan dopracowania (polish) po MVP

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ujednolicić UX funkcji powiązań (tabele, modal, strona grupy), dodać pełne zarządzanie z rozwiniętych wierszy przez reuse `SettlementOperationsSection` (**podejście B**), oraz pokazywać tytuł grupy przy ikonie w wierszu — bez regresji API poza rozszerzeniem pól list.

**Architecture:**  
- **B:** W trzech listach (zunifikowana, bank, gotówka) w treści `renderExpandedRow` dodać sekcję z `SettlementOperationsSection` tylko dla `source_type === "bank" | "cash"` (jak na `bank-transactions/[id]` / `cash-transactions/[id]`). Jeden wiersz = jeden `useQuery` `by-transaction` w tym komponencie; React Query deduplikuje, cache ogranicza ruch.  
- **Tytuł grupy w liście:** jedno pole opcjonalne z JOIN do `settlement_groups.title` (np. `settlement_group_title`) w odpowiedziach trzech list + Zod; UI: ikona + skrót tekstu + tooltip / `title`.  
- **Modal `LinkOperationsModal`:** `Modal` z jawnie szeroką kolumną (np. `maxWidth` rozszerzone lub wyłączny `forwardUpstreamResponse` już zrobiony dla 204) + osobna lista „Przypięte” (bieżąca + zaznaczone) niezależna od wyszukiwarki — zgodnie z [spec: Procesy powiązywania](../specs/2026-04-22-transaction-settlement-bundles-design.md).  
- **Strona `/settlement-groups/[id]`:** tabela członków z kolumnami jak lista zunifikowana, **bez** kategorii, typu transakcji bankowej, źródła gotówki; kolumna źródła = tylko `SourceBadge` jak w `app/page.tsx` (główne kolumny tabeli, bez `showLabel`).

**Tech stack:** Next.js 14, React Query, Zod, FastAPI, psycopg2, repozytoria jak w [planie MVP](2026-04-23-transaction-settlement-bundles.md).

**Odniesienia:** [design MVP](../specs/2026-04-22-transaction-settlement-bundles-design.md) · [plan MVP](2026-04-23-transaction-settlement-bundles.md)

**Już zrobione (nie powtarzać w PR jako nowa praca):** błąd 500 po `DELETE` grupy z powodu `204` + pustego ciała w proxy — `frontend/lib/proxy.ts` (`forwardUpstreamResponse`); wersja frontendu podbita (np. 1.4.3).

---

## Mapa plików (szacowana)

| Obszar | Pliki |
|--------|--------|
| Backend: tytuł grupy w listach | `backend/src/data.py` (modele list), `unified_transactions.py`, `bank_transactions.py`, `cash_transactions.py` (SELECT + join `settlement_groups`), ewent. test integracyjny list |
| Proxy | `frontend/lib/proxy.ts` — **bez zmian** jeśli 204 fix już na branchu |
| Typy + API | `frontend/lib/types.ts`, `frontend/lib/api.ts` (jeśli tylko typy z backendu) |
| Modal łączenia | `frontend/components/LinkOperationsModal.tsx`, ewent. `frontend/components/ui/Modal.tsx` (nowy wariant `maxWidth` / `2xl` / `4xl` lub tylko `className` + `tailwind-merge` w `Modal` żeby uniknąć konfliktu `max-w-md` vs `max-w-4xl`) |
| Sekcja powiązań (reuse) | `frontend/components/SettlementOperationsSection.tsx` (menu trzy kropki zamiast pełnoszerokich przycisków destrukcyjnych) |
| Strona grupy | `frontend/app/settlement-groups/[id]/page.tsx` — tabela z `DataTable` / te same kolumny co główne listy (uprość do uzgodnionego zestawu) |
| Wiersz zunifikowany | `frontend/app/page.tsx` — `ExpandedRow` + kolumna settlement (ikona + tytuł) |
| Wiersz banku | `frontend/app/bank-transactions/page.tsx` — `ExpandedRowContent` + kolumna settlement |
| Wiersz gotówki | `frontend/app/cash-transactions/page.tsx` — to samo |

---

## Faza A — Backend: `settlement_group_title` (nullable)

- [ ] **A.1** W `data.py` dodać do modeli listowych: `settlement_group_title: str | None` obok `settlement_group_id` (`UnifiedTransaction`, `BankTransactionListItem`, `CashTransactionListItem` — nazywać spójnie z resztą repo).

- [ ] **A.2** W zapytaniach `get_list` (unified / bank / cash) dołączyć tytuł z `settlement_groups` po `settlement_group_id` (ten sam `LEFT JOIN` co do id grupy, dodatkowa kolumna `sg.title`).

- [ ] **A.3** Test: integracja lub unit repo — jedna transakcja w grupie z tytułem → w liście jest `settlement_group_title == "…"`, bez grupy → `null`.

---

## Faza B — Modal: szerokość + „Przypięte”

- [ ] **B.1** `Modal`: upewnić się, że docelowa szerokość (np. `max-w-4xl` / `5xl`) **wygrywa** z domyślnym `max-w-md` (np. `tailwind-merge` w `clsx` albo nowy `maxWidth: "4xl"` w `maxWidthClasses` + użycie w `LinkOperationsModal`).

- [ ] **B.2** `LinkOperationsModal`: dodać sekcję listy **Przypięte** (bieżąca transakcja + wszystkie zaznaczone checkboxem) z przyciskiem usunięcia z przypięć (z wyjątkiem „kotwicy” bieżącej, jeśli spec tak ma — dopasuj do copy w specu). Wyniki wyszukiwania poniżej; zaznaczenie = dodanie do przypiętych, niezależnie od kolejnej zmiany frazy.

- [ ] **B.3** `POST` dalej jednym requestem: `members` = bieżąca + wszystkie przypięte (deduplikacja po `source_type`+`id`).

- [ ] **B.4** Ręcznie: brak poziomego scrollbara na typowym desktopie przy normalnych danych (lub tylko wewnątrz tabeli wyników, nie całego modala).

---

## Faza C — `SettlementOperationsSection`: menu trzy kropki

- [ ] **C.1** Dla destrukcyjnych / drugorzędnych akcji (np. „Odepnij”, „Przenieś…”, „Usuń całą grupę”) użyć `ThreeDotsMenu` (`frontend/components/ui/ThreeDotsMenu.tsx`) w tej samej konwencji co inne tabeli/strony w appce — zamiast wielu pełnej szerokości `Button` w jednym rzędzie, o ile wzorzec jest spójny z innymi ekranami (inline `variant="inline"`).

- [ ] **C.2** Zostawić 1–2 główne CTA (np. „Utwórz z wybranych…”, link do strony grupy) jako dotychczas, jeśli tak jest na detalu banku.

---

## Faza D — Strona `/settlement-groups/[id]`: tabela „Operacje w zestawie”

- [ ] **D.1** Zastąpić `<ul>` tabelą z nagłówkami (kolumny: np. `SourceBadge` (bank/gotówka), data, opis (vendor/desc), kwota, ewent. akcja w menu — spójnie z tabelą zunifikowaną; **nie** dawać: kategorii, typu transakcji bank., źródła gotówki w osobnych kolumnach).

- [ ] **D.2** Użyć tych samych komponentów co lista: `Amount`, `SourceBadge` bez etykiety jak w głównej tabeli `page.tsx` (`<SourceBadge source={r.source_type} />` w kolumnach — por. ok. linii 560 w `app/page.tsx`).

---

## Faza E — Podejście B: `SettlementOperationsSection` w expandach

- [ ] **E.1** `frontend/app/page.tsx` — w `ExpandedRow`, gdy `isLinkable`, pod istniejącym blokiem (np. po ostatniej sekcji lub przed / po — wybierz spójny układ) renderować:
  - `<SettlementOperationsSection sourceType="bank" | "cash" transactionId={row.id} />`  
  (tylko `bank`/`cash`).

- [ ] **E.2** `frontend/app/bank-transactions/page.tsx` — w `ExpandedRowContent` dodać `SettlementOperationsSection` z `sourceType="bank"`, `transactionId={tx.id}`.

- [ ] **E.3** `frontend/app/cash-transactions/page.tsx` — w `ExpandedRowContent` dodać `SettlementOperationsSection` z `sourceType="cash"`, `transactionId={tx.id}`.

- [ ] **E.4** Sprawdzić, że `SettlementOperationsSection` po mutacjach invaliduje te same `queryKey` co dziś, plus ewent. `["transactions"]` / listy — tak aby expand i główne listy odświeżały `settlement_group_id` / tytuł.

---

## Faza F — Kolumna w wierszu: ikona + tytuł grupy

- [ ] **F.1** W trzech plikach list (`page.tsx` unified, `bank-transactions/page.tsx`, `cash-transactions/page.tsx`) w komórce powiązań: jeśli `settlement_group_id`, pokazać `Link` do `/settlement-groups/{id}` z ikoną (`Link2`); jeśli `settlement_group_title` — skrót obok (np. `truncate max-w-[10rem]`) i `title` atrybut / `Tooltip` z pełną nazwą.

- [ ] **F.2** Upewnić się, że wiersze paragonu (`receipt`) nie łamią typów (pole `null` albo brak w schemacie dla receipt).

---

## Faza G — Przyciski / rozmiary (przegląd)

- [ ] **G.1** Przejść sekcję powiązań, `LinkOperationsModal`, nagłówek strony grupy: porównać `Button` z listami transakcji; użyć `size="sm"` tam, gdzie reszta tabel używa mniejszych kontrolek (jeśli design system przewiduje `size`).

- [ ] **G.2** Dostosować wyłącznie w tym obszarze — bez globalnych zmian `Button` defaults.

---

## Faza H — Weryfikacja

- [ ] **H.1** `npm run lint` + `npm run build` w `frontend/`.

- [ ] **H.2** `backend` — testy dotknięte pliki (repo lub integracja) + ruff/mypy wg `backend/AGENTS.md`.

- [ ] **H.3** Przebieg ręczny: utwórz grupę z modala (przypięte + 2+ operacje) → wiersz pokazuje ikonę + tytuł → expand → ta sama sekcja co na detalu → usuń grupę (204) → brak 500.  
- [ ] **H.4** Zgodnie z `frontend/AGENTS.md`: podbić `version` w `package.json` + `package-lock.json` po stronie frontendu (patch vs minor wg zakresu).

---

## Kolejność rekomendowana

1. A (backend + typy) → F (UI list) zależą od tytułu.  
2. B (modal) równolegle z C/D po typach.  
3. E (expand + `SettlementOperationsSection`) — po A (query keys mogą wymagać tytułu tylko w F, E jest niezależne).  
4. G → H.

---

## Ryzyka

- **Dwa razy `by-transaction`:** użytkownik otwiera detal strony + expand — dwa mounty `SettlementOperationsSection`; cache React Query to norma, ewent. `staleTime` zostaw domyślny, chyba że obciążenie będzie zauważalne.  
- **Długie tytuły grupy:** w kolumnie zawsze `truncate` + pełny tekst w tooltip.  
- **Responsywność modala:** v1 desktop; wąskie okna mogą wymagać tylko `overflow-x-auto` wewnątrz tabeli wyników (akceptowalne).

---

## Uwaga prawna / scope

Nie rozszerzać tego planu o mobile-first ani o zmiany backendu poza `settlement_group_title` + testami, chyba że pojawi się regresja.
