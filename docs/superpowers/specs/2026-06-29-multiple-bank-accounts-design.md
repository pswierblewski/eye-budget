# Design: Obsługa wielu kont bankowych

**Data:** 2026-06-29
**Status:** Zatwierdzony

---

## Kontekst i cel

Aplikacja obsługuje aktualnie tylko jedno konto bankowe (import CSV Pekao SA).
Użytkownik ma 3 konta: Pekao SA (główne), Pekao SA (drugie), Revolut.

Cel:
- Pełny CRUD zarządzania kontami bankowymi w UI
- Obsługa importu CSV Revolut (inny format niż Pekao)
- Widok agregujący konta na stronie `/bank-transactions` (karty + filtr)
- Kolumna "Konto" w głównej tabeli zbiorczej (`/`)

---

## Decyzje projektowe

| Pytanie | Odpowiedź |
|---|---|
| Zarządzanie kontami | Pełny CRUD w UI (modal na `/bank-transactions`) |
| Widok agregujący | Karty podsumowania u góry `/bank-transactions` + filtr pill w tabeli |
| Oznaczenie w głównej tabeli | Dodatkowa kolumna "Konto" — tylko dla wierszy bankowych, puste dla pozostałych |
| Deduplikacja Revolut | `SHA256(account_id + started_date + description + amount)` |
| Architektura | Tabela `bank_accounts` z FK na `bank_transactions` |

---

## Sekcja 1: Model danych

### Nowa tabela

```sql
CREATE TABLE bank_accounts (
    id        SERIAL PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    bank_type VARCHAR(50)  NOT NULL,  -- 'pekao' | 'revolut' | 'other'
    color     VARCHAR(20)  NOT NULL DEFAULT 'blue',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### Zmiana na `bank_transactions`

```sql
ALTER TABLE bank_transactions
ADD COLUMN account_id INTEGER REFERENCES bank_accounts(id) ON DELETE SET NULL;
```

### Migracja danych

Tworzy konto `"Pekao SA"` (`bank_type='pekao'`, `color='blue'`) i ustawia `account_id` na wszystkich istniejących transakcjach — brak NULL-i w danych historycznych.

### Klucz deduplikacji Revolut

`SHA256(account_id || started_date || description || amount)` — generowany po stronie backendu przed insertem, zapewnia idempotentny ponowny import tego samego pliku CSV.

---

## Sekcja 2: Backend

### Nowe repozytorium `BankAccountsRepository`

- `list()` → lista kont z agregowanymi statystykami (suma przychodów, suma wydatków, liczba transakcji) — jedno zapytanie z LEFT JOIN na `bank_transactions`
- `create(name, bank_type, color)` → INSERT
- `update(id, name, color)` → UPDATE (`bank_type` niezmienialne po utworzeniu)
- `delete(id)` → DELETE z guardem: 409 jeśli konto ma transakcje

### Nowe endpointy

```
GET    /bank-accounts          → lista kont + statystyki
POST   /bank-accounts          → utwórz konto
PUT    /bank-accounts/{id}     → edytuj nazwę/kolor
DELETE /bank-accounts/{id}     → usuń (guard: brak transakcji)
```

### Import CSV — zmiana

`POST /bank-transactions/import` dostaje dodatkowo `account_id: int` jako form field obok pliku. Backend pobiera konto, wybiera parser na podstawie `bank_type`:
- `pekao` → `PekaoCsvParser` (istniejący)
- `revolut` → `RevolutCsvParser` (nowy)
- `other` → `PekaoCsvParser` jako fallback

### Nowy `RevolutCsvParser`

Osobna klasa analogiczna do `PekaoCsvParser`. Format wejściowy (CSV angielski, przecinki):

```
Type, Product, Started Date, Completed Date, Description, Amount, Fee, Currency, State, Balance
```

Mapowanie kolumn:
- `Started Date` → `booking_date`
- `Completed Date` → `value_date`
- `Description` → `description`
- `Amount` → `amount`
- `Currency` → `currency`
- `Type` → `operation_type`
- `State == REVERTED` → wiersz pomijany
- `reference_number` → `SHA256(account_id + started_date + description + amount)`

### Zmiany w istniejących repozytoriach

- `BankTransactionsRepository.get_list()` → opcjonalny parametr `account_id: Optional[int]` dodany do WHERE
- `UnifiedTransactionsRepository.get_list()` → LEFT JOIN `bank_accounts` na gałęzi bankowej, nowe pole `account_name` w SELECT
- `BankTransactionListItem` i `UnifiedTransaction` w `data.py` → nowe pola `account_id: Optional[int]`, `account_name: Optional[str]`

---

## Sekcja 3: Frontend — strona `/bank-transactions`

### Karty podsumowania kont

Poziomy rząd kart u góry strony, jedna karta per konto. Karta zawiera:
- Nazwę konta z kolorowym wskaźnikiem (kolor z pola `color` konta)
- Sumę przychodów i wydatków
- Liczbę transakcji
- Klikalność: kliknięcie ustawia filtr tabeli na dane konto

Dane pobierane z `GET /bank-accounts` (zawiera statystyki).

### Import CSV

Przycisk "Import CSV" otwiera najpierw dropdown/select z listą kont, po wyborze konta — standardowy file picker. Jeśli brak kont — wyświetlany link/przycisk do dodania konta.

### Filtr po koncie

Pill-bary nad tabelą: "Wszystkie" + po jednym pillu per konto (nazwa + kolorowy wskaźnik). Kliknięcie karty podsumowania synchronizuje ten filtr.

### Zarządzanie kontami (CRUD)

Przycisk "Zarządzaj kontami" obok "Import CSV" otwiera modal z:
- Listą istniejących kont (nazwa, typ, kolor) z akcjami edytuj / usuń
- Formularzem dodawania nowego konta: nazwa (text), bank_type (select: Pekao SA / Revolut / Inne), kolor (select lub color picker)
- Usunięcie zablokowane jeśli konto ma transakcje — tooltip z wyjaśnieniem

---

## Sekcja 4: Frontend — główna tabela `/`

### Nowa kolumna "Konto"

Dodana między kolumną "Typ" a "Datą". Dla wierszy bankowych wyświetla nazwę konta z małą kolorową kropką (kolor konta). Dla `cash` i `receipt` — puste pole (nic nie wyświetlane).

### Zmiany w typach

`UnifiedTransaction` (w `lib/types.ts`) rozszerzone o:
```typescript
account_id: number | null;
account_name: string | null;
```

`SourceBadge` pozostaje bez zmian — kolumna "Konto" jest osobnym miejscem.

---

## Sekcja 5: Testowanie

### Backend — unit testy

- `RevolutCsvParser`: parsowanie poprawnych wierszy, filtrowanie REVERTED, generowanie klucza SHA256, obsługa brakujących pól
- `BankAccountsRepository`: create, list ze statystykami, update, delete z guardem 409
- `BankTransactionsRepository.get_list()`: filtr po `account_id`

### Backend — testy integracyjne

- `POST /bank-accounts` + `GET /bank-accounts`
- `DELETE /bank-accounts/{id}` przy istniejących transakcjach → 409
- `POST /bank-transactions/import` z `account_id` → weryfikacja przypisania transakcji

### Frontend

Brak nowych unit testów — komponenty UI nie są testowane w projekcie. Istniejące testy Vitest (`bankTxCategoryListUi.ts`) nie wymagają zmian.
