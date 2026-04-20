# Lista transakcji bankowych — propozycja AI kategorii + realtime (Pusher)

**Date:** 2026-04-20  
**Status:** Draft (ready for review)  
**Suggested branch:** `feature/bank-tx-list-ai-category`

---

## Problem

Po zapisaniu propozycji kategorii przez LLM w tle użytkownik widzi je dopiero po odświeżeniu listy. Na liście `/bank-transactions` brak jest widocznej **najlepszej propozycji** oraz szybkiej akcji **„Zapisz kategorię”**, mimo że szczegóły transakcji już zwracają `category_candidates`.

---

## Scope

- **Strona:** lista transakcji bankowych (`/bank-transactions`), kolumna „Kategoria”.
- **UI:** zatwierdzony układ makiet (`category-cell-layout-v3`): jedna linia — nazwa top kandydata, opcjonalnie wskaźnik pewności (np. `0,87`), przycisk **`Button` `variant="secondary"` `size="sm"`** — etykieta „Zapisz kategorię”; **bez** prefiksu „AI:”.
- **Realtime:** po zapisaniu kandydatów dla pojedynczej transakcji w zadaniu Celery frontend **aktualizuje wiersz** bez pełnego przeładowania (Pusher, kanał już używany: `bank-transactions`).
- **Poza zakresem:** zmiana logiki LLM, zmiana schematu zapisu `category_candidates` w DB, edycja propozycji na liście (tylko top + jeden klik zapisu).

---

## Reguły widoczności (produkt)

| Stan wiersza | Top propozycja + „Zapisz kategorię” |
|---|---|
| Użytkownik ma przypisaną kategorię (`category_id` / wyświetlana nazwa w gałęzi pojedynczej) | **Ukryte** |
| Kategorie z **powiązanego paragonu** (jak dziś: `receipt_category_name` / badge +N) | **Ukryte** |
| **Podział** na wiele kategorii (`split_count >= 2` jak w obecnej kolumnie) | **Ukryte** |
| Brak przypisania użytkownika, brak powyższych stanów, są zapisani kandydaci LLM | **Widoczne** — zawsze **top** z listy (nawet jeśli w JSON jest wiele kandydatów); jednym kliknięciem zapisujemy **top** |

---

## Opcje techniczne (backend + Pusher)

### Opcja 1 — List API + zdarzenie per transakcja (rekomendowana)

- **GET lista:** rozszerzyć `BankTransactionListItem` o pola wystarczające do wyświetlenia top propozycji, np. opcjonalnie `ai_top_candidate: { category_id, category_name, category_score } | null` (lub płaskie pola), wyliczane z `category_candidates` w repozytorium (sort po `category_score` malejąco, pierwszy element).
- **Celery:** po `update_candidates` dla danego `tx_id` wywołać `PusherService.trigger` na kanale `bank-transactions`, nowe zdarzenie, np. `categorization.transaction_updated`, payload: `{ bank_transaction_id, ai_top_candidate }` (lub minimalny zestaw pól zsynchronizowany z listą).
- **Frontend:** subskrypcja (globalna na stronie lub przy imporcie / ponownej kategoryzacji) — przy evencie **merge** do cache React Query dla `["bank-transactions", …]` (aktualizacja jednego elementu `items` po `id`) **albo** `invalidateQueries` jeśli merge jest zbyt kosztowny w pierwszej iteracji; `categorization.done` może zostać jako dodatkowe `invalidateQueries` dla spójności.

**Plusy:** dokładne realtime po wierszu, jedno źródło prawdy jak lista. **Minusy:** kontrakt API + nowe zdarzenie do utrzymania.

### Opcja 2 — Tylko `categorization.progress` z `transaction_id`

- Rozszerzyć payload `categorization.progress` o `bank_transaction_id`; frontend przy każdym kroku robi `invalidateQueries` lub `refetch` listy.

**Plusy:** mniej zdarzeń. **Minusy:** więcej ruchu sieciowego i obciążenia listy przy dużych batchach.

### Opcja 3 — Wyłącznie invalidate na `progress`

- Bez zmiany payloadu — częstsze odświeżanie całej listy.

**Odrzucone:** gorsze UX i skalowanie przy wielu wierszach.

**Rekomendacja:** **Opcja 1**.

---

## Frontend — zachowanie

- Komórka „Kategoria”: dla kwalifikujących się wierszy renderować `flex` / `flex-wrap` / `gap` jak w istniejących gałęziach paragon/split; przycisk **`stopPropagation`**, żeby klik nie zwijał/rozwijał wiersza.
- Subskrypcja Pusher: unikać wielokrotnego `subscribe` na ten sam kanał bez potrzeby (np. jeden kanał na montaż strony + `bind` na `categorization.transaction_updated`, cleanup przy odmontowaniu).
- Po sukcesie `saveBankTransactionCategory` — jak dziś invalidacja zapytań; upewnić się, że propozycja i przycisk znikają zgodnie z regułami.

---

## Testy (wymagane)

- **Backend (unit):** wyliczanie top kandydata z listy JSON; że `categorization.transaction_updated` (lub ustalona nazwa) jest emitowane z oczekiwanym payloadem po `update_candidates` (mock `PusherService`, wzorzec jak w `test_categorize_bank_transactions.py`).
- **Frontend (unit):** funkcja pomocnicza lub test komponentu — reguły widoczności przycisku / top dla zadanych propsów (przypisana kategoria, paragon, split, brak kandydatów, wielu kandydatów z top).

---

## Feature branch i PR

- Praca na osobnym branchu, np. `feature/bank-tx-list-ai-category`; merge po review i przejściu testów / quality gates projektu.

---

## Self-review (checklist)

- [x] Reguła „wiele kandydatów LLM” — zawsze top + przycisk, jeśli wiersz kwalifikuje się jako „nie przypisane”.
- [x] Paragon / split — przycisk ukryty; nie używamy słowa „konflikt” w UI.
- [x] Prefiks „AI:” — brak.
- [x] Realtime — Pusher, kanał `bank-transactions`, nowe zdarzenie per transakcja (Opcja 1).
