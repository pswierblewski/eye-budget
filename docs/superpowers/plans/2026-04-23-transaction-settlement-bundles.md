# Powiązane operacje (settlement groups) — plan implementacji

> **Odniesienie:** [docs/superpowers/specs/2026-04-22-transaction-settlement-bundles-design.md](../specs/2026-04-22-transaction-settlement-bundles-design.md) (źródło prawdy).  
> **Branch (sugestia):** `feature/transaction-settlement-bundles`

**Cel:** Grupy `settlement_groups` + członkowie `settlement_group_members` (tylko bank / gotówka), API z listą, detailem, bilansem, paragonami z istniejących linków, UI desktop (lista grup z badge, szczegóły transakcji, modale), ikony na listach, **wariant (A):** grupę kasuje tylko użytkownik; **jeden** `POST` przy tworzeniu grupy z modala z pełnym `members`.

**Stack:** Backend: Python/FastAPI, psycopg2, Pydantic v2, Yoyo. Frontend: Next.js 14, React Query, Zod, `lib/api.ts`, thin `app/api/**/route.ts`.

---

## Mapa plików (konkretyzacja pod repo `eye-budget`)

Poniżej: **pełne ścieżki**, powiązania i kolejność, żeby nic nie zostawić na „dopisz później”.

### Backend — nowe

| Plik | Rola |
|------|------|
| `backend/migrations/20260423_01_settlement_groups.sql` | Nazwa robocza: przed `yoyo apply` zweryfikuj **następny wolny** numer. W nagłówku: `depends: 20260421_01_wynagrodzenie-category-parent` (ostatnia migracja w drzewie w momencie pisania planu) — przed commitem upewnij się, czy na `master` nie doszła nowsza; wtedy `depends` musi wskazywać **faktyczny** ostatni plik. Zawartość: `settlement_groups`, `settlement_group_members`, indeksy (w tym `UNIQUE` częściowe), **bez** triggera kasującego grupy. |
| `backend/src/repositories/settlement_groups.py` | `SettlementGroupsRepository` (jak inne w `repositories/`: wstrzyknięcie `EyeBudgetDbContext`, kursor, `commit`/`rollback`). Metody: tworzenie grupy + wielu członków w jednej transakcji, lista z `search` + `member_count`, `get_by_id` z członkami, bilans, `linked_receipts` (join do `receipt_bank_links` / `receipt_cash_links` + `receipts_scans`), `add_member` / `remove_member` / `delete_group`, helper `get_group_id_for_member(source, id)`. O ile repozytorium trzyma referencję do połączenia: **`dispose()`** jak w `bank_transactions.py`. |
| `backend/tests/unit/test_settlement_groups_repository.py` | Testy na prawdziwym PG w kontenerze (wzór: `test_unified_transactions_repository.py` / `test_bank_receipt_links_repository.py`) albo, jeśli ograniczacie się do integracji API, tylko plik integracyjny — **minimum:** jeden z dwóch poziomów musi walidować SQL. |
| `backend/tests/integration/test_settlement_groups_routes.py` | Wzorzec: `test_bank_transaction_splits_routes.py` — `TestClient` z `src.main`, `pytest.mark.integration`, fixture `migrated_db` / `client` z `tests/integration/conftest.py` (jeśli wymagane: dopisać do migracji testowej inicjowanie nowych tabel albo użyć tego samego stosu co splits). |

### Backend — modyfikacje (obowiązkowe)

| Plik | Co zmienić |
|------|------------|
| `backend/src/data.py` | Nowe modele: `CreateSettlementGroupRequest`, `UpdateSettlementGroupRequest`, `AddSettlementMemberRequest`, `SettlementGroupMemberId` (source + id), `SettlementMemberRow`, `LinkedReceiptSummary` (lub re-use istniejącego kształtu z list paragonów), `SettlementGroupListItem`, `SettlementGroupDetail` (z `total_expense`, `total_income`, `net`, `member_count`). Rozszerzyć: `UnifiedTransaction` — pole `settlement_group_id: int \| None`. `BankTransactionListItem` / `BankTransactionDetail` / `CashTransactionListItem` / `CashTransactionDetail` — to samo pole (detail opcjonalnie, jeśli front i tak woła `by-transaction`). |
| `backend/src/repositories/unified_transactions.py` | W `get_list` (i `COUNT` w tym samym kształcie co główne `SELECT`): dodać `settlement_group_id` przez `LEFT JOIN settlement_group_members` (osobne joiny na bank i cash w gałęziach `UNION` albo `COALESCE` z podzapytaniem). **Dokładna pozycja:** tam, gdzie dziś `LEFT JOIN` do `receipt_*_links`. |
| `backend/src/repositories/bank_transactions.py` | W `get_list` / `get_by_id`: odczyt `settlement_group_id` (ten sam wzorzec `LEFT JOIN` `settlement_group_members` po `bt.id = bank_transaction_id`). |
| `backend/src/repositories/cash_transactions.py` | Analogicznie dla `cash_transaction_id`. |
| `backend/src/app.py` | **Import:** `from .repositories.settlement_groups import SettlementGroupsRepository`. W `__init__`: parametr opcjonalny `settlement_groups_repository=None`, przypisanie `self.settlement_groups_repository = ... or SettlementGroupsRepository(self.eye_budget_db_context)`. W `dispose()`: `self.settlement_groups_repository.dispose()` (jeśli repozytorium ma `dispose`). **Metody publiczne** (nazwy do uzgodnienia 1:1 z `main.py`): np. `list_settlement_groups`, `create_settlement_group`, `get_settlement_group`, `get_settlement_group_by_transaction`, `update_settlement_group`, `delete_settlement_group`, `add_settlement_group_member`, `remove_settlement_group_member` — w środku: walidacje 409, mapowanie na DTO, orkiestracja `bank_receipt_links` tylko jako read przez repo grup. |
| `backend/src/main.py` | Dla każdej trasy: `from src.data import` nowych modeli; endpointy: `GET/POST /settlement-groups`, `GET/PATCH/DELETE /settlement-groups/{id}`, `GET /settlement-groups/by-transaction`, `POST/DELETE /settlement-groups/{id}/members` — wzorzec `my_app = App(); try: ...; finally: my_app.dispose()`. Import request body z `data.py`. Odpowiedzi: `PaginatedResponse[SettlementGroupListItem]` na listę (jak `/bank-transactions`). **Uwaga routingu FastAPI:** ścieżka statyczna `/settlement-groups/by-transaction` musi być zarejestrowana **przed** lub w sposób niekolidujący z `/{id}` (FastAPI: route bardziej specyficzna musi być trafiana pierwsza — w praktyce zdefiniuj `by-transaction` przed `/{id}` w pliku albo użyj prefiksu). |
| `backend/tests/unit/conftest.py` | Dodać `"settlement_groups_repository"` do listy `ALL_PARAMS`, żeby `make_app()` nie wymusiał prawdziwego DB. |

### Frontend — nowe (trasy `app/`, API proxy, komponenty)

| Plik | Rola |
|------|------|
| `frontend/app/api/settlement-groups/route.ts` | `GET` → `proxyGet("/settlement-groups?...")` (przekaż `searchParams` jak w `app/api/bank-transactions/route.ts`); `POST` → `proxyPost` + body JSON. |
| `frontend/app/api/settlement-groups/[id]/route.ts` | `GET`, `PATCH`, `DELETE` na `/settlement-groups/{id}`. Wzorzec: `app/api/bank-transactions/[id]/route.ts`. |
| `frontend/app/api/settlement-groups/[id]/members/route.ts` | `POST` (body: `{ source_type, id }` — dokładna nazwa pól = Zod w `types.ts`); `DELETE` z query: `?source_type=bank&transaction_id=123` (jeśli backend tak definiuje) — **spójnie** z `main.py` (bez ciała `DELETE` jeśli `proxyDelete` nie przekazuje body). |
| `frontend/app/api/settlement-groups/by-transaction/route.ts` | Tylko `GET`; `searchParams` → backend `/settlement-groups/by-transaction?...` |

**Kolejność katalogów:** utwórz `by-transaction` i `[id]/members` równolegle z `types.ts` — Next wymaga istnienia `route.ts` przed stroną.

| Plik | Rola |
|------|------|
| `frontend/app/settlement-groups/page.tsx` | Lista: `"use client"`, tabela, `useQuery` z `listSettlementGroups`, pole szukaj, przycisk nowej pustej grupy, nawigacja do `/settlement-groups/[id]`, badge (patrz spec). |
| `frontend/app/settlement-groups/[id]/page.tsx` | Detal: `useQuery` + `getSettlementGroup`, bilans, lista członków z `Link` do `/bank-transactions/[id]` (**bank**) i **`/cash-transactions/[id]`** (**gotówka** — po dodaniu prostego detailu, patrz wiersz poniżej). |
| `frontend/app/cash-transactions/[id]/page.tsx` | **Nowy, prosty widok** pojedynczej transakcji gotówkowej. Źródło danych: istniejące `getCashTransaction(id)` → `CashTransactionDetail`. **Zakres treści = to, co widać w kolumnach wiersza** na `cash-transactions/page.tsx` (bez kopiowania całego `ExpandedRowContent`): data (`isoToDisplay(booking_date)`), opis / sklep (jak w kolumnie: `vendor_name` + ewent. druga linia `description`), **kwota** (`Amount`), **kategoria** (gałąź z paragonu vs ręczna — jak w kolumnie `Kategoria`: `receipt_category_name` / `receipt_category_count` vs `category_name`), **źródło** (`SourceBadge`), **tagi** (`Pill`). Layout: `PageHeader` + sekcje (`SectionLabel`) lub jedna karta — spójnie z `bank-transactions/[id]/page.tsx` (uprość). Link **Wstecz** do `/cash-transactions`. Sekcja **„Powiązane operacje”** (ten sam komponent / wzorzec co bank) **w zakresie tego samego feature** — w planie: umieścić ją na tej stronie albo zaimportować wspólny `SettlementSection` gdy będzie. |
| `frontend/components/SettlementGroupBadge.tsx` (lub w `ui/`) | Mały **badge** z liczbą: `CountBadge` / `Badge` + `className` warunkowe dla `count === 0` — re-use na stronie listy i w pickerze. |
| `frontend/components/SettlementGroupPickerModal.tsx` | Tabela/compact lista z tych samych danych co strona główna grup; wyszukiwanie; wybór → callback `onSelect(groupId)`; w środku `listSettlementGroups` + ten sam komponent badge. |
| `frontend/components/LinkOperationsModal.tsx` (nazwa robocza) | Modal: strefa przypiętych, lista zunifikowana (najpewniej wyciągnąć fragment tabeli z `app/page.tsx` albo wspólny `UnifiedTransactionsPickerTable` w `components/`). Walidacja ≥2 łącznie → `createSettlementGroup`. |

### Frontend — modyfikacje

| Plik | Co zmienić |
|------|------------|
| `frontend/lib/types.ts` | Schematy Zod dla wszystkich DTO z `data.py`; rozszerzenie schematów `UnifiedTransaction`, `BankTransactionListItem`, `CashTransactionListItem` (+ detale, jeśli używane w UI). |
| `frontend/lib/api.ts` | Funkcje: `listSettlementGroups`, `getSettlementGroup`, `getSettlementGroupByTransaction`, `createSettlementGroup`, `updateSettlementGroup`, `deleteSettlementGroup`, `addSettlementGroupMember`, `removeSettlementGroupMember` — każda woła odpowiedni `fetch` na `/api/settlement-groups/...`. |
| `frontend/components/Sidebar.tsx` | Nowy `navItems`: `{ href: "/settlement-groups", label: "…", icon: Link2 }` (lub `Users` — unikać ikony sugerującej „split”) — pozycja względem „Budżet” wg UX; w tym pliku `navItems` jest jedną tablicą. |
| `frontend/app/page.tsx` | Kolumna z ikoną `Link2` gdy `settlement_group_id` ustawione; `Link` do `/settlement-groups/{id}`. **Poprawka linku gotówki:** w `UnifiedTxExpandedRow` (lub gdzie jest `detailHref`) obecnie `row.source_type === "cash"` → `href: "/cash-transactions"` — po dodaniu `cash-transactions/[id]/page.tsx` ustawić na **`/cash-transactions/${row.id}`** (jak dla banku). Mutacje: `invalidateQueries` dla `settlement-groups` po zmianach. |
| `frontend/app/bank-transactions/page.tsx` | Ta sama kolumna (jeśli tabela główna; jeśli tylko link do `/bank-transactions/[id]`, tylko ikonka w wierszu). |
| `frontend/app/bank-transactions/[id]/page.tsx` | Nowa sekcja „Powiązane operacje”: stan z `getSettlementGroupByTransaction` albo `settlement_group_id` z `getBankTransaction`; CTA, modale. |
| `frontend/app/cash-transactions/page.tsx` | (1) Dodać **nawigację do detailu** — np. `Link` z daty, opisu lub osobna kolumna / ikona strzałki → `/cash-transactions/[id]` (żeby z listy dało się wejść w prosty widok). (2) Rozszerzony wiersz (`ExpandedRowContent`) zostaje do pełnej edycji; **sekcja „Powiązane operacje”** docelowo też na **`/cash-transactions/[id]`** (spójność z bankiem) — ewent. duplikacja krótka: najpierw detail + sekcja, później opcjonalnie skrót w expandzie. |

### Migracja — jedna linia do skopiowania

```
depends: 20260421_01_wynagrodzenie-category-parent
```

(Podmień na **aktualny** ostatni plik w `backend/migrations/` w momencie implementacji.)

---

## Faza 1 — Baza i repozytorium

- [ ] **1.1 Migracja SQL** — plik: `backend/migrations/<timestamp>_settlement_groups.sql` (nazwa + `depends` wg sekcji *Mapa*).  
  - Tabele jak w specu; **brak** triggera `AFTER DELETE` na `settlement_group_members` usuwającego `settlement_groups`.  
  - Lokalnie: `yoyo apply` (workflow jak w innych planach) + `\d` / `SELECT`.

- [ ] **1.2 `SettlementGroupsRepository`** — plik: `backend/src/repositories/settlement_groups.py`.  
  - `create_group(title, note, members[])` w jednej transakcji: `INSERT settlement_groups` + `INSERT` wielu członków; obsługa `members=[]`.  
  - `get_by_id`, `get_list(search, limit, offset, sort)` + `member_count` (subquery / join).  
  - `get_group_id_for_transaction(source_type, id) -> int | None`  
  - `add_member` / `remove_member` / `delete_group`  
  - **Bilans** + **`linked_receipts`** (join do istniejących tabel linków + `receipts_scans`).

- [ ] **1.3 Testy** — `backend/tests/unit/test_settlement_groups_repository.py` **lub** tylko `backend/tests/integration/test_settlement_groups_routes.py` + fixture z `conftest` integracyjnego; przypadki: pusta grupa, konflikt unikalności, bilans, `remove_member` do zera (grupa **zostaje**).

---

## Faza 2 — Warstwa App + HTTP

- [ ] **2.1 Modele** — `backend/src/data.py`: request/response DTO (patrz tabela w *Mapie*).  
- [ ] **2.2 `App`** — `backend/src/app.py`: pole `settlement_groups_repository`, `dispose`, publiczne metody pod endpointy.  
- [ ] **2.3 `main.py`**: wszystkie trasy; **`GET /settlement-groups/by-transaction` zarejestrowane tak, by nie była łapana jako `{id}`** (np. wpisać deklarację `by-transaction` przed `/{id}` albo użyć osobnej ścieżki — zweryfikować w runtime). `PaginatedResponse[SettlementGroupListItem]` na listę. **409/404** jak w innych zasobach.  
- [ ] **2.4** — `backend/tests/integration/test_settlement_groups_routes.py` + ewent. aktualizacja `backend/tests/integration/conftest.py` jeśli migracje wymagają seedu.

---

## Faza 3 — Listy transakcji: `settlement_group_id`

- [ ] **3.1** Rozszerzyć SQL w `UnifiedTransactionsRepository.get_list` o `settlement_group_id` (left join / scalar subquery na `settlement_group_members`).

- [ ] **3.2** To samo dla list banku i gotówki (jeśli używane w UI z ikoną).

- [ ] **3.3** Dodać pole do odpowiednich modeli Pydantic listowych i ewentualnie do detalu transakcji, jeśli front potrzebuje bez drugiego requestu (minimalnie: `settlement_group_id` na liście wystarczy do linku/ikonki; szczegóły grupy ładowane przez `by-transaction` lub `GET` grupy po id).

---

## Faza 4 — Frontend: typy, API, proxy

- [ ] **4.1** `frontend/lib/types.ts` — Zod + `z.infer` (patrz *Mapa*).  
- [ ] **4.2** `frontend/lib/api.ts` — wszystkie funkcje; po mutacjach: `invalidateQueries` dla `["settlement-groups"]`, `["transactions", ...]`, `["bank-transactions", ...]`, `["cash-transactions", ...]` zgodnie z `queryKey` używanymi na stronach.  
- [ ] **4.3** Pliki `frontend/app/api/settlement-groups/**/route.ts` (pełne drzewo w *Mapie*). Import `proxyGet` / `proxyPost` / `proxyPatch` / `proxyDelete` z `@/lib/proxy` — nie wołać backendu z komponentu.

---

## Faza 5 — UI: strony grup

- [ ] **5.1 `/settlement-groups`** — tabela/karty: tytuł, data, **`member_count` jako Badge**; **`member_count === 0`** — inna klasa (np. `variant` z `components/ui` / stonowany kolor, **nie** czerwony błąd). Wyszukiwanie po `search`, paginacja, przycisk **„Nowa pusta grupa”** → `POST { members: [] }` z opcjonalnym tytułem w dialogu.

- [ ] **5.2 `/settlement-groups/[id]`** — tytuł, notatka, bilans (neutralny), lista członków z linkami do `/bank-transactions/{id}` (**bank**) i `/cash-transactions/{id}` (**gotówka**; wymaga istniejącej strony z *Mapy*). Skrót paragonów, akcja **Usuń grupę** (potwierdzenie), edycja `PATCH` title/note jeśli w specu.

- [ ] **5.3 Picker (modal)** — wspólny komponent listy z `GET /settlement-groups?search=` (compact); te same reguły badge dla 0.

- [ ] **5.4 `Sidebar`** — wpis nawigacji (np. „Powiązane operacje” / krótka etykieta) → `/settlement-groups`; ikona zgodna z użyciem na listach (np. `Link2` / `Users` — unikać „Split” w copy).

---

## Faza 6 — UI: transakcje (detail + listy)

- [ ] **6.0 Prosty detail gotówki (wymaga wcześniej niż pełne „Powiązane” na gotówce, jeśli linki z grup mają działać)** — plik: `frontend/app/cash-transactions/[id]/page.tsx`. `useQuery` + `getCashTransaction` + `useParams`. Treść: **tylko pola odpowiadające kolumnom tabeli** (patrz *Mapa* / `columns` w `cash-transactions/page.tsx`: Data, Opis/sklep, Kwota, Kategoria, Źródło, Tagi). **Bez** obowiązku przenoszenia edycji kategorii / paragonu z `ExpandedRowContent` w v1 (zostają na liście w expandzie). Dopisek: proxy `GET` już jest (`frontend/app/api/cash-transactions/[id]/route.ts`); nowa strona tylko w `app/`.

- [ ] **6.0b** `frontend/app/cash-transactions/page.tsx` — dodać linki do `/cash-transactions/[id]` (wiersz tabeli), żeby UX był spójny z bankiem. **`frontend/app/page.tsx`:** zaktualizować `detailHref` dla wierszy `source_type === "cash"` (z *Mapy*).

- [ ] **6.1 Sekcja „Powiązane operacje”** na stronie detalu **transakcji bankowej** (`bank-transactions/[id]/page.tsx`) oraz na **nowym** detalu gotówki (`cash-transactions/[id]/page.tsx`):  
  - brak `settlement_group_id` → CTA: **Utwórz** (modal) oraz **Dołącz do istniejącej** (picker).  
  - jest w grupie → `GET` grupy, lista pozostałych, paragony, bilans, dodawanie / rozłącz.

- [ ] **6.2 Modal z listą zunifikowaną** — reuse komponentów / stylu z `app/page.tsx` (tabela, filtry, search); strefa **Przypięte**; wykluczyć z wyników wyszukiwania zduplikowane id; `POST` jednym requestem.

- [ ] **6.3 Ikona na listach** — `frontend/app/page.tsx`, `bank-transactions/page.tsx`, `cash-transactions/page.tsx`: kolumna z ikoną gdy `settlement_group_id` ustawione; klik opcjonalnie → `/settlement-groups/{id}`.

---

## Faza 7 — Weryfikacja

- [ ] **7.1** Ręczny przebieg scenariuszy **A–F** z sekcji speca (Burrata + prod sample ids jeśli DB dostępna).

- [ ] **7.2** `backend` — testy + ewent. `ruff`/`mypy` zgodnie z repo.

- [ ] **7.3** `frontend` — `npm run lint`, `npm run build`.

- [ ] **7.4** Zgodnie z `frontend/AGENTS.md`: po zmianach frontendu — podbić `version` w `package.json` + lockfile (minor przy nowym feature).

- [ ] **7.5** Spec design ma już **Status: Approved**; po merge ewentualnie dopisać link do PR w opisie commita.

---

## Kolejność rekomendowana (skrót)

1. Migracja + repo + modele + trasy + testy API.  
2. Rozszerzenie list transakcji o `settlement_group_id`.  
3. **`/cash-transactions/[id]`** (prosty detail) + linki z listy gotówki.  
4. Strony `/settlement-groups` + sidebar.  
5. Sekcja „Powiązane operacje” + modale na `bank-transactions/[id]`, `cash-transactions/[id]`, ikony na listach.  
6. Testy E2E manualne, wersja.

---

## Ryzyka / uwagi

- **Bilans:** ujednolicić znak `amount` (wyciąg: wydatki ujemne) — spisać w teście jedną tabelkę przykładów.  
- **CASCADE:** usunięcie transakcji usunie tylko membership; pusta grupa zostaje — użytkownik sprząta z listy (badge „0” ma to ułatwiać).  
- **Wydajność:** `member_count` na liście grup — lepiej w jednym zapytaniu niż N+1.  
- **Spójność list/detail gotówki:** prosty `/cash-transactions/[id]` nie zastępuje expanded row — użytkownik nadal może edytować z listy; uniknąć rozjazdu copy (ta sama logika etykiet kolumn).  
- **FastAPI path conflict:** upewnić się, że `.../by-transaction` nie mapuje się na `{id}` (test uruchomieniowy: `GET` z `source_type`/`transaction_id`).  
- **DELETE member:** jeśli backend wymaga body, a `proxyDelete` nie przekazuje ciała — użyć `DELETE` z query string albo dodać cienką obudowę w `proxy.ts` (tylko jeśli konieczne; preferowane: query, jak w specu).
