# Paragony — naprawa przycisku „Wyczyść” w filtrach zaawansowanych

**Date:** 2026-08-18
**Status:** Approved
**Suggested branch:** `fix/receipts-clear-filters`

---

## Problem

Na stronie `/receipts` przycisk **„Wyczyść”** w pasku narzędzi (widoczny gdy `activeFilterCount > 0`) ma błędny handler:

```tsx
onClick={() => setFiltersOpen(true)}
```

Zamiast czyścić zastosowane filtry zaawansowane, **tylko otwiera panel filtrów**. Lista paragonów pozostaje przefiltrowana; badge licznika aktywnych filtrów nie znika.

Dodatkowy defekt pomocniczy: `FilterPanel` przy mount wywołuje `onCountChange(0)`, co zeruje licznik w rodzicu nawet gdy filtry są nadal aktywne (np. po otwarciu panelu przy już zastosowanych filtrach).

---

## Scope

- **Tylko** `frontend/app/receipts/page.tsx`.
- **W zakresie:** przycisk „Wyczyść” w pasku narzędzi, reset stanu filtrów zaawansowanych, usunięcie błędnego efektu mount w `FilterPanel`, `key` reset panelu przy czyszczeniu.
- **Poza zakresem:** synchronizacja pól `FilterPanel` z `appliedFilters` przy ponownym otwarciu panelu (osobny task UX); reset filtra statusu (zakładki Wszystkie / Do potwierdzenia / …); zmiany backendu; inne strony (`/` transakcje).

---

## Zachowanie docelowe

### Przycisk „Wyczyść” (pasek narzędzi)

Widoczny gdy `activeFilterCount > 0`. Po kliknięciu:

1. `appliedFilters` → `EMPTY_FILTERS`
2. `activeFilterCount` → `0`
3. `page` → `1`
4. Inkrementacja `filterPanelKey` (wymusza remount `FilterPanel` z pustym stanem lokalnym, gdy panel jest otwarty)
5. **Bez zmian:** `statusFilter`, `filtersOpen` (panel nie otwiera się ani nie zamyka automatycznie)

### Przycisk „Wyczyść filtry” (wewnątrz panelu)

Bez zmian — czyści lokalny stan `FilterPanel`; istniejący efekt propaguje pusty stan do rodzica przez `onChange`.

### Po wyczyszczeniu

- React Query odświeża listę (`queryKey` zawiera `appliedFilters`) bez filtrów zaawansowanych.
- Badge „Filtry (N)” znika.
- Zakładka statusu pozostaje bez zmian.

---

## Podejście techniczne

**A — szybka poprawka handlera + `key` reset (wybrane).**

W `ReceiptsPage`:

```typescript
const [filterPanelKey, setFilterPanelKey] = useState(0);

const clearAdvancedFilters = useCallback(() => {
  setAppliedFilters(EMPTY_FILTERS);
  setActiveFilterCount(0);
  setPage(1);
  setFilterPanelKey((k) => k + 1);
}, []);
```

Toolbar „Wyczyść”: `onClick={clearAdvancedFilters}`.

`FilterPanel`:

```tsx
<FilterPanel
  key={filterPanelKey}
  onChange={handleFiltersChange}
  onCountChange={handleFilterCountChange}
  allTags={allTags}
/>
```

Usunąć:

```typescript
useEffect(() => { onCountChange(0); }, [onCountChange]);
```

**Odrzucone alternatywy:**

- **B — panel w pełni kontrolowany** (`value` + `onChange` z rodzica): poprawia synchronizację pól przy ponownym otwarciu, ale ~60–80 linii refactoru — poza zakresem bugfixa.
- **C — sygnał resetu (`resetSignal`)** bez remountu: dodatkowa złożoność bez korzyści względem `key`.

---

## Wersjonowanie

PATCH frontendu (`frontend/package.json` + `package-lock.json`) — poprawka błędu UI, bez nowej funkcjonalności.

---

## Testy / weryfikacja

| # | Scenariusz | Oczekiwany wynik |
|---|-----------|------------------|
| 1 | Ustaw filtr zaawansowany (np. sklep) → „Wyczyść” w pasku | Lista bez filtra; badge znika; status bez zmian |
| 2 | Panel otwarty + filtry → „Wyczyść” w pasku | Pola w panelu puste; lista odświeżona |
| 3 | Panel otwarty → „Wyczyść filtry” w panelu | Identycznie jak #1 |
| 4 | Filtr zaawansowany + status „Do potwierdzenia" → „Wyczyść" | Status zostaje; filtry zaawansowane wyczyszczone |
| 5 | Brak filtrów zaawansowanych | Przycisk „Wyczyść" niewidoczny |

Automatyczne:

- `npm run lint` (frontend)
- `npx tsc --noEmit` (frontend)

Brak nowych testów jednostkowych — logika to settery stanu React; zgodnie z konwencją drobnych poprawek UI w repo.

---

## Self-review

- [x] Brak TBD / placeholderów.
- [x] Zakres ograniczony do jednego pliku FE.
- [x] Status filter wyłączony z czyszczenia (zgodnie z decyzją użytkownika).
- [x] Desynchronizacja pól panelu przy ponownym otwarciu świadomie poza zakresem.
- [x] Wersjonowanie: PATCH FE only.
