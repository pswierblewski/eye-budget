# Powiązane operacje (settlement groups) — plan implementacji

> **Odniesienie:** [docs/superpowers/specs/2026-04-22-transaction-settlement-bundles-design.md](../specs/2026-04-22-transaction-settlement-bundles-design.md) (źródło prawdy).  
> **Branch (sugestia):** `feature/transaction-settlement-bundles`

**Cel:** Grupy `settlement_groups` + członkowie `settlement_group_members` (tylko bank / gotówka), API z listą, detailem, bilansem, paragonami z istniejących linków, UI desktop (lista grup z badge, szczegóły transakcji, modale), ikony na listach, **wariant (A):** grupę kasuje tylko użytkownik; **jeden** `POST` przy tworzeniu grupy z modala z pełnym `members`.

**Stack:** Backend: Python/FastAPI, psycopg2, Pydantic v2, Yoyo. Frontend: Next.js 14, React Query, Zod, `lib/api.ts`, thin `app/api/**/route.ts`.

---

## Mapa plików (z grubsza)

**Nowe (backend):**
- `backend/migrations/20260423_01_settlement_groups.sql` (lub kolejny wolny numer w `migrations/`)
- `backend/src/repositories/settlement_groups.py`
- `backend/tests/unit/test_settlement_groups_repository.py` (opcjonalnie)
- `backend/tests/integration/test_settlement_groups_routes.py` (lub rozszerzenie istniejącego wzorca `app` tests)

**Nowe (frontend):**
- `frontend/app/settlement-groups/page.tsx` — lista
- `frontend/app/settlement-groups/[id]/page.tsx` — detal grupy
- `frontend/app/api/settlement-groups/...` — proxy (zgodnie z wzorcem: `[id]/route.ts`, `[id]/members/route.ts`, `by-transaction/route.ts` itd. — ułożyć analogicznie do innych zasobów)
- `frontend/components/...` — sekcja „Powiązane operacje”, modale (nazwy do ustalenia: np. `SettlementGroupPickerModal`, `LinkOperationsModal`)

**Modyfikacje (najważniejsze):**
- `backend/src/data.py` — modele `SettlementGroupDetail`, `SettlementGroupListItem`, `SettlementMember`, rozszerzenia list: `settlement_group_id` na `UnifiedTransaction`, `BankTransactionListItem`, `CashTransactionListItem`, analogicznie detale
- `backend/src/repositories/unified_transactions.py` — `LEFT JOIN` / podzapytanie `settlement_group_members`
- `backend/src/repositories/bank_transactions.py` / `cash_transactions.py` — to samo dla list i `get_by_id` jeśli potrzebne do sekcji w detailu
- `backend/src/app.py` + `backend/src/main.py` — metody + trasy
- `frontend/lib/types.ts`, `frontend/lib/api.ts`
- `frontend/app/bank-transactions/[id]/page.tsx`, `frontend/app/cash-transactions/...` (jeśli jest detail), `frontend/app/page.tsx` (unified) — kolumna ikony + sekcja
- `frontend/components/Sidebar.tsx` — link do `/settlement-groups`

**Zależność migracji:** `depends:` na ostatni plik w `backend/migrations/` (obecnie sensowny punkt: po tabelach `bank_transactions`, `cash_transactions` — użyj **nazwy pliku** ostatniej migracji w repo, np. `20260421_01_wynagrodzenie-category-parent`).

---

## Faza 1 — Baza i repozytorium

- [ ] **1.1 Migracja SQL**  
  - Tabele jak w specu (`settlement_groups`, `settlement_group_members`, indeksy unikalne częściowe na `bank_transaction_id` / `cash_transaction_id`, `idx_sgm_group`).  
  - **Brak** triggera `AFTER DELETE` usuwającego grupę po liczniku.  
  - `yoyo apply` lokalnie; `\d` w `psql` / szybki `SELECT` sanity.

- [ ] **1.2 `SettlementGroupsRepository`**  
  - `create_group(title, note, members[])` w jednej transakcji: `INSERT settlement_groups` + `INSERT` wielu członków; obsługa `members=[]`.  
  - `get_by_id`, `get_list(search, limit, offset, sort)` + `member_count` (np. `COUNT` subquery lub join agregujący).  
  - `get_group_id_for_transaction(source_type, id) -> int | None`  
  - `add_member(group_id, source_type, id)`; `remove_member`  
  - `delete_group`  
  - **Bilans:** funkcja licząca `total_expense`, `total_income`, `net` po `amount` z `bank_transactions` / `cash_transactions` dla `id` w grupie (dopasuj znak do konwencji wyciągu w projekcie — jeden arbitralny wariant opisany w teście).  
  - **`linked_receipts`:** zapytania do `receipt_bank_links` / `receipt_cash_links` + metadane skanu; deduplikacja po `receipts_scans.id`.

- [ ] **1.3 Testy repozytorium** (jeśli macie wzorzec unit z PG): pusta grupa, `POST` wielu członków, 409-ekwiwalent w repo (unikalność), bilans, usunięcie ostatniego członka **zostawia** grupę.

---

## Faza 2 — Warstwa App + HTTP

- [ ] **2.1 Modele Pydantic** w `data.py` zgodne ze specem (`SettlementGroupDetail`, list item, request body dla `POST` / `PATCH` / `DELETE members`).

- [ ] **2.2 `App` (interfejs w `app.py`)**  
  - Metody wywołujące repozytorium; **409** gdy transakcja już w innej grupie; **404** gdy brak grupy.  
  - `GET by-transaction` → ten sam DTO co `GET /{id}` albo 404.

- [ ] **2.3 `main.py` — rejestracja ścieżek**  
  - `GET/POST /settlement-groups`  
  - `GET/PATCH/DELETE /settlement-groups/{id}`  
  - `POST/DELETE /settlement-groups/{id}/members`  
  - `GET /settlement-groups/by-transaction` (query: `source_type`, `transaction_id`)  
  - Spójnie z `PaginatedResponse` jeśli reszta list tak robi.

- [ ] **2.4 Testy integracyjne API** (FastAPI TestClient / istniejący wzorzec): happy path, pusta grupa, dodanie członka, usunięcie członka (grupa zostaje), `DELETE` grupy, `by-transaction`.

---

## Faza 3 — Listy transakcji: `settlement_group_id`

- [ ] **3.1** Rozszerzyć SQL w `UnifiedTransactionsRepository.get_list` o `settlement_group_id` (left join / scalar subquery na `settlement_group_members`).

- [ ] **3.2** To samo dla list banku i gotówki (jeśli używane w UI z ikoną).

- [ ] **3.3** Dodać pole do odpowiednich modeli Pydantic listowych i ewentualnie do detalu transakcji, jeśli front potrzebuje bez drugiego requestu (minimalnie: `settlement_group_id` na liście wystarczy do linku/ikonki; szczegóły grupy ładowane przez `by-transaction` lub `GET` grupy po id).

---

## Faza 4 — Frontend: typy, API, proxy

- [ ] **4.1 `frontend/lib/types.ts`** — schematy Zod dla wszystkich DTO (grupa, lista, member, linked receipt summary, bilans).

- [ ] **4.2 `frontend/lib/api.ts`** — funkcje wywołujące proxy; `invalidateQueries` po mutacjach (listy transakcji, grupy, opcjonalnie pojedyncza transakcja).

- [ ] **4.3 `frontend/app/api/settlement-groups/**`** — cienkie proxy do backendu (jak w `AGENTS.md`).

---

## Faza 5 — UI: strony grup

- [ ] **5.1 `/settlement-groups`** — tabela/karty: tytuł, data, **`member_count` jako Badge**; **`member_count === 0`** — inna klasa (np. `variant` z `components/ui` / stonowany kolor, **nie** czerwony błąd). Wyszukiwanie po `search`, paginacja, przycisk **„Nowa pusta grupa”** → `POST { members: [] }` z opcjonalnym tytułem w dialogu.

- [ ] **5.2 `/settlement-groups/[id]`** — tytuł, notatka, bilans (neutralny), lista członków z linkami do `/bank-transactions/...` lub `/cash-transactions/...`, skrót paragonów, akcja **Usuń grupę** (potwierdzenie), edycja `PATCH` title/note jeśli w specu.

- [ ] **5.3 Picker (modal)** — wspólny komponent listy z `GET /settlement-groups?search=` (compact); te same reguły badge dla 0.

- [ ] **5.4 `Sidebar`** — wpis nawigacji (np. „Powiązane operacje” / krótka etykieta) → `/settlement-groups`; ikona zgodna z użyciem na listach (np. `Link2` / `Users` — unikać „Split” w copy).

---

## Faza 6 — UI: transakcje (detail + listy)

- [ ] **6.1 Sekcja „Powiązane operacje”** na stronie detalu **transakcji bankowej** (i gotówkowej, jeśli jest osobny detail):  
  - brak `settlement_group_id` → CTA: **Utwórz** (otwarcie modala z unified list + przypięcia; walidacja ≥2 łącznie przed `POST`) oraz **Dołącz do istniejącej** (picker).  
  - jest w grupie → `GET` grupy (`by-transaction` lub `/{id}`), lista pozostałych, paragony, bilans, dodawanie kolejnych (`POST members` / modal), rozłącz / usuń z grupy.

- [ ] **6.2 Modal z listą zunifikowaną** — reuse komponentów / stylu z `app/page.tsx` (tabela, filtry, search); strefa **Przypięte**; wykluczyć z wyników wyszukiwania zduplikowane id; `POST` jednym requestem.

- [ ] **6.3 Ikona na listach** — `frontend/app/page.tsx`, `bank-transactions/page.tsx`, `cash-transactions/page.tsx` (oraz wiersz rozwijany, jeśli dotyczy): kolumna z ikoną gdy `settlement_group_id` ustawione; klik opcjonalnie → `/settlement-groups/{id}`.

---

## Faza 7 — Weryfikacja

- [ ] **7.1** Ręczny przebieg scenariuszy **A–F** z sekcji speca (Burrata + prod sample ids jeśli DB dostępna).

- [ ] **7.2** `backend` — testy + ewent. `ruff`/`mypy` zgodnie z repo.

- [ ] **7.3** `frontend` — `npm run lint`, `npm run build`.

- [ ] **7.4** Zgodnie z `frontend/AGENTS.md`: po zmianach frontendu — podbić `version` w `package.json` + lockfile (minor przy nowym feature).

- [ ] **7.5** Uaktualnić **Status** w pliku design na *Approved* po merge / akceptacji QA.

---

## Kolejność rekomendowana (skrót)

1. Migracja + repo + modele + trasy + testy API.  
2. Rozszerzenie list transakcji o `settlement_group_id`.  
3. Strony `/settlement-groups` + sidebar.  
4. Sekcja + modale na detailach + ikony na listach.  
5. Testy E2E manualne, wersja, status speca.

---

## Ryzyka / uwagi

- **Bilans:** ujednolicić znak `amount` (wyciąg: wydatki ujemne) — spisać w teście jedną tabelkę przykładów.  
- **CASCADE:** usunięcie transakcji usunie tylko membership; pusta grupa zostaje — użytkownik sprząta z listy (badge „0” ma to ułatwiać).  
- **Wydajność:** `member_count` na liście grup — lepiej w jednym zapytaniu niż N+1.
