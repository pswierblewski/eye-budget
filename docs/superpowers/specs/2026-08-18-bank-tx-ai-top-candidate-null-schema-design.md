# Bank transactions — akceptacja `ai_top_candidate: null` w schemacie Zod

**Date:** 2026-08-18  
**Status:** Approved (brainstorming)  
**Suggested branch:** `fix/bank-tx-ai-top-candidate-null-schema`

---

## Problem

Po imporcie CSV na stronie **Transakcje bankowe** podczas kategoryzacji w tle (pasek „Kategoryzacja… X/Y”) przez ułamek sekundy (czasem dłużej) pojawia się czerwony panel `QueryState`:

> Nie udało się pobrać transakcji bankowych.

Z technicznym komunikatem walidacji Zod dla każdego wiersza listy:

```json
{ "code": "invalid_type", "expected": "object", "received": "null", "path": ["items", N, "ai_top_candidate"], "message": "Expected object, received null" }
```

**Przyczyna:** Backend (FastAPI / Pydantic) zwraca `ai_top_candidate: null`, gdy transakcja nie ma jeszcze kandydatów AI (`BankTransactionListItem.ai_top_candidate: CategoryCandidate | None = None` w `backend/src/data.py`). To zamierzone — m.in. Celery emituje Pusher z `ai_top_candidate: null` gdy brak kandydatów (`test_emits_null_ai_top_when_no_valid_candidate`).

Frontend w `BankTransactionListItemSchema` ma:

```ts
ai_top_candidate: CategoryCandidateSchema.optional(),
```

W Zod `.optional()` akceptuje brak pola lub `undefined`, ale **nie** `null`. Po imporcie CSV strona wywołuje `queryClient.invalidateQueries({ queryKey: ["bank-transactions"] })`, co refetchuje listę **zanim** kategoryzacja zakończy się dla wszystkich pozycji — odpowiedź HTTP jest poprawna (200), ale `schema.parse()` w `apiFetch` odrzuca JSON.

Handler Pushera (`payload.ai_top_candidate ?? undefined`) normalizuje `null` w cache React Query, lecz **nie** obejmuje refetchu z API.

**Potwierdzony scenariusz reprodukcji:** tylko po imporcie CSV (nowe transakcje + kategoryzacja w tle), nie przy „Ponów kategoryzację” ani zwykłym odświeżeniu strony.

---

## Scope

**W zakresie:**

- `frontend/lib/types.ts` — dopasowanie `BankTransactionListItemSchema.ai_top_candidate` do kontraktu backendu
- `frontend/lib/bankTransactionListSchema.test.ts` — test regresji parsowania odpowiedzi z `null`
- bump wersji frontendu PATCH (`package.json`, `package-lock.json`)

**Poza zakresem:**

- zmiany backendu (kontrakt jest poprawny)
- opóźnianie `invalidateQueries` po imporcie (nowe wiersze muszą się pojawić od razu; Pusher nie dodaje nowych rekordów do listy)
- refaktor `QueryState` / `placeholderData` (maskowałby symptom, nie naprawia root cause)
- zmiany w handlerze Pushera (opcjonalnie zostaje bez zmian)

---

## Rozwiązanie (podejście A — wybrane)

### Schemat Zod

W `BankTransactionListItemSchema`:

```ts
// było:
ai_top_candidate: CategoryCandidateSchema.optional(),

// będzie:
ai_top_candidate: CategoryCandidateSchema.nullable().optional(),
```

Spójne z innymi polami listy (`category_id`, `receipt_category_name` itd.). Typ wynikowy: `CategoryCandidate | null | undefined`.

Istniejący kod UI (`shouldShowAiCategoryProposal`, warunki `t.ai_top_candidate && …`) już traktuje `null`/`undefined` jako brak propozycji — **bez zmian w komponentach**.

### Odrzucone alternatywy

| Podejście | Powód odrzucenia |
|-----------|------------------|
| B — refetch dopiero po `categorization.done` | Nowe wiersze po imporcie nie pojawiłyby się w tabeli bez dodatkowej logiki |
| C — `QueryState` z `keepPreviousData` | Nie naprawia pierwszego refetchu po imporcie; ukrywa błąd walidacji |

---

## Testy

Plik `frontend/lib/bankTransactionListSchema.test.ts` (Vitest, `@vitest-environment node`), wzorzec jak `bankTxCategoryListUi.test.ts`:

1. Parsuje paginowaną odpowiedź z `items[].ai_top_candidate: null`
2. Parsuje odpowiedź z obiektem kandydata (regresja pozytywna)
3. Parsuje odpowiedź bez pola `ai_top_candidate` (opcjonalność)

Uruchomienie: `cd frontend && npm run test:run`.

---

## Wersjonowanie

Frontend PATCH: `1.8.2` → `1.8.3` (`package.json` + `package-lock.json` root i `packages[""].version`). Backend bez zmian.

---

## Weryfikacja ręczna

1. Import CSV z nowymi transakcjami (kategoryzacja w tle).
2. W trakcie paska „Kategoryzacja… X/Y” — brak czerwonego `QueryState`.
3. Propozycje AI pojawiają się stopniowo (Pusher).
4. Po zakończeniu kategoryzacji — lista kompletna, bez błędu.

---

## Self-review

- [x] Brak TBD / placeholderów.
- [x] Root cause i kontrakt API opisane jednoznacznie.
- [x] Zakres ograniczony do schematu + test + wersja FE.
- [x] UI i backend pozostają bez zmian — zgodne z YAGNI.
- [x] Scenariusz reprodukcji (tylko import CSV) uwzględniony w specyfikacji.
