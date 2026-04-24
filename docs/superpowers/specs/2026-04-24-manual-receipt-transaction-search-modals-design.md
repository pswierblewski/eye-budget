# Ręczne wyszukiwanie paragonu ↔ transakcji (modale) — design

**Status:** zatwierdzony (brainstorming 2026-04-24)  
**Data:** 2026-04-24  
**Kontekst:** Łączenie paragonu z transakcją bankową/gotówkową opiera się m.in. na heurystyce (np. równa kwota i okno dat ±2 dni w repozytoriach). W e-commerce płatność i data paragonu mogą być oddalone — kandydaci automatyczni często nie wystarczą. Potrzebne są modale wyszukiwania z jednym polem, spójne z `LinkOperationsModal` (powiązane operacje).

## Decyzje użytkownika (zamknięte)

| Temat | Wybór |
|--------|--------|
| Interfejs wyszukiwania | **A** — jedno pole wyszukiwania (jak w `LinkOperationsModal`). |
| Prefill z transakcji → paragon | **A** — wstaw **kwotę** (pole + niewidoczne filtry `total_min` / `total_max` — sekcja 3). |
| Prefill z paragonu → transakcje | **A** — zawsze **kwota** paragona w tym samym sensie. |
| Wyniki na listach | **B** — pełne wyniki; już sparowane: **przygaszone** + etykieta, **bez** „zmień powiązanie” w modalu. |
| Podejście danych | **1** — rozszerzyć `listReceipts` o flagi/identyfikator; `listUnifiedTransactions` z istniejącymi `has_receipt` / `receipt_scan_id`. |

## Cel

Umożliwić ręczne dokończenie pary: **transakcja (bank / gotówka) ↔ paragon** oraz **paragon → transakcja (bank + gotówka)**, w modalu z wyszukiwarką, we wszystkich wskazanych miejscach UI.

## Miejsca w UI (sekcja 1)

- **Wyszukaj paragon** (z prefill **kwotą** transakcji): rozwinięty wiersz i widok szczegółów na stronach transakcji **bankowych** i **gotówkowych**; obecny flow kandydatów uzupełnić / powiązać z tym samym modałem, gdzie ma sens.
- **Wyszukaj transakcję (bank + gotówka)** (z prefill **kwotą** paragonu): rozwinięty wiersz na liście paragonów oraz widok szczegółów paragonu (`/receipts/[id]`).

**Akcja:** tylko **„Powiąż”** dla wierszy dopuszczalnych; dla już sparowanych (w sensie B) brak głównego CTA; dla bieżącego powiązania (ten sam `receipt_scan_id` / ten sam link) — etykieta w stylu „Aktualne powiązanie”, bez ponownego linkowania.

## Struktura modali i UX (sekcja 2)

- **Dwa modale** (nazwy implementacyjne na etapie kodu): wyszukanie paragonu z kontekstu transakcji; wyszukanie transakcji z kontekstu paragonu.
- **Układ** jak `LinkOperationsModal`: `Modal`, jedno pole **Szukaj**, lista wyników (np. limit 40), obsługa ładowania i pustki.
- **Prefill:** pole startuje sformatowaną kwotą kotwicy; równolegle ustawiane są filtry numeryczne (sekcja 3), bo ogólne `search` u listy paragonów nie obejmuje `total` w tym samym zapytaniu.
- Wiersze: przycisk **Powiąż** | przygaszenie + „Już powiązane” | „Aktualne powiązanie” według reguł w sekcji 3.

## Dane, API, zapytania (sekcja 3, podejście 1)

### `listReceipts` (paragony w modalu z transakcji)

- Rozszerzyć `ReceiptScanListItem` o m.in.:
  - **`receipt_transaction_id`** (nullable) — wymagane do `POST` linku, gdy transakcja paragonu jest potwierdzona.
  - **`has_transaction_link`** (lub równoważne) — do wyszarzania w wariancie B.
- Repozytorium: wykorzystać `LEFT JOIN receipt_transactions` i `EXISTS` (lub join) do tabel linków.
- Wiersze **bez** `receipt_transaction_id`: w implementacji ujednolicić — minimalnie: **„Powiąż”** tylko gdy `receipt_transaction_id` jest (albo jawny komunikat wymagający potwierdzenia skanu), żeby uniknąć martwego CTA.

### `listUnifiedTransactions` (transakcje w modalu z paragonu)

- Reguły wyszarzania: `has_receipt` i `receipt_scan_id` vs bieżący skan (obcy link vs aktualne powiązanie) — opis w sekcji „Decyzje” powyżej.
- **Zakres typów:** tylko `bank` i `cash`. Przy obecnym API z pojedynczym `source_type`: albo **dwa zapytania** z tymi samymi filtrami + merge i sort, albo rozszerzenie API — **decyzja w planie implementacji** z poprawną semantyką `total` / offset.
- **Filtry kwoty:** paragony: `total_min` / `total_max` na |kwota kotwicy|; transakcje: `amount_min` / `amount_max` spójne z regułą `ABS` jak przy łączeniu (szczegół w planie technicznym).

## Błędy i sukces (sekcja 4)

- Wykorzystać `linkBankToReceipt` / `linkCashToReceipt` (i symetrię cash/bank względem istniejących endpointów); konflikty (409) — komunikaty spójne z resztą aplikacji.
- Po sukcesie: invalidacja zapytań analogiczna do obecnego ręcznego łączenia, zamknięcie modala.

## Testy (sekcja 5)

- **Backend / repozytorium / API:** nowe pola w `listReceipts`, poprawność flag i `receipt_transaction_id`.
- **Frontend:** zachowanie modali, wyszarzenia wg B, happy path + błąd API.

## Proces wydania (implementacja)

Zgodnie z `AGENTS.md` i `context.md` — **osobne SemVer** dla frontu i backu. Przy tej zmianie (nowe, wstecz zgodne pola listy, nowe zachowanie UI) typowo: **MINOR** w `frontend/package.json` (+ `package-lock.json`) oraz **MINOR** w `backend/src/version.py` (+ asercja w `tests/unit/test_version.py`).

- **Branch:** praca na **dedykowanym branchu** feature (nie commity bezpośrednio na główny; merge po review).
- **Testy:** obowiązkowe przed merge (w tym weryfikacja wersji jeśli dotykana).

## Powiązania w kodzie (orientacyjnie)

- Wzorzec modala: `frontend/components/LinkOperationsModal.tsx` (`listUnifiedTransactions`).
- Listy: `listReceipts`, `listUnifiedTransactions` w `frontend/lib/api.ts`.
- Heurystyka okna dat: `backend/src/repositories/bank_receipt_links.py` / `cash_receipt_links.py` (`find_receipt_candidates`).

---

*Po akceptacji tego pliku następny krok: plan implementacji (`writing-plans`), nie implementacja w tej samej turze spec.*
