# Paragony — naprawa przycisku „Wyczyść” — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Naprawić przycisk „Wyczyść” na `/receipts`, aby resetował filtry zaawansowane (nie otwierał panelu) i synchronizował stan panelu z rodzicem.

**Architecture:** Lokalna poprawka w `ReceiptsPage` — nowy handler `clearAdvancedFilters` resetuje `appliedFilters`, licznik i stronę; `filterPanelKey` wymusza remount `FilterPanel` przy czyszczeniu. Usunięcie błędnego efektu mount w `FilterPanel`, który zerował licznik filtrów.

**Tech Stack:** Next.js 14 / React 18 / TypeScript / React Query v5 (frontend).

**Spec:** `docs/superpowers/specs/2026-08-18-receipts-clear-filters-design.md`

## Global Constraints

- UI copy: polski (bez nowych stringów).
- SemVer PATCH po ukończeniu: tylko `frontend/package.json` + `frontend/package-lock.json` (root i `packages[""].version`) — obecna wersja `1.8.3` → `1.8.4`.
- Zakres: wyłącznie `frontend/app/receipts/page.tsx`.
- Nie resetować `statusFilter` przy „Wyczyść”.
- Nie modyfikuj `.env` / `.env.agent`.
- Brak nowych testów jednostkowych (zgodnie ze spec).

---

## Pliki objęte zmianą

| Plik | Odpowiedzialność |
|------|------------------|
| `frontend/app/receipts/page.tsx` | Handler czyszczenia, `filterPanelKey`, fix toolbar, usunięcie błędnego efektu w `FilterPanel` |
| `frontend/package.json` | PATCH wersji FE |
| `frontend/package-lock.json` | PATCH wersji FE (root + `packages[""].version`) |

**Bez zmian:** backend, inne strony, `FilterTabs`, API.

---

### Task 1: FilterPanel — usunięcie błędnego efektu mount

**Files:**
- Modify: `frontend/app/receipts/page.tsx:236-237`

**Interfaces:**
- Consumes: `FilterPanel` props `onChange`, `onCountChange` (bez zmian).
- Produces: `FilterPanel` nie wywołuje `onCountChange(0)` przy mount — licznik w rodzicu pozostaje zgodny z aktywnymi filtrami po otwarciu panelu.

- [ ] **Step 1: Usuń efekt zerujący licznik przy mount**

W `FilterPanel`, usuń cały blok (linie 236–237):

```typescript
  // Also report initial count (0)
  useEffect(() => { onCountChange(0); }, [onCountChange]);
```

Po usunięciu sekcja kończy się bezpośrednio na:

```typescript
  }, [applied, onChange, onCountChange]);

  const set = <K extends keyof FilterValues>(key: K, value: FilterValues[K]) =>
```

- [ ] **Step 2: Sprawdź lint i typy**

Run:
```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Expected: brak nowych błędów.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/receipts/page.tsx
git commit -m "fix(frontend): stop FilterPanel from resetting active filter count on mount"
```

---

### Task 2: ReceiptsPage — handler czyszczenia i naprawa toolbar

**Files:**
- Modify: `frontend/app/receipts/page.tsx:315-326,707-714,764-766`

**Interfaces:**
- Consumes: `EMPTY_FILTERS`, `FilterValues`, istniejące `handleFiltersChange`, `handleFilterCountChange`.
- Produces: `clearAdvancedFilters(): void` — reset filtrów zaawansowanych; toolbar „Wyczyść" woła tę funkcję; `FilterPanel` renderowany z `key={filterPanelKey}`.

- [ ] **Step 1: Dodaj stan `filterPanelKey` i handler `clearAdvancedFilters`**

W `ReceiptsPage`, zaraz po linii z `activeFilterCount` (obecnie ~317), dodaj:

```typescript
  const [filterPanelKey, setFilterPanelKey] = useState(0);
```

Zaraz po `handleFilterCountChange` (~326), dodaj:

```typescript
  const clearAdvancedFilters = useCallback(() => {
    setAppliedFilters(EMPTY_FILTERS);
    setActiveFilterCount(0);
    setPage(1);
    setFilterPanelKey((k) => k + 1);
  }, []);
```

- [ ] **Step 2: Napraw przycisk „Wyczyść" w toolbarze**

Zamień (obecnie ~707–714):

```tsx
        {activeFilterCount > 0 && (
          <button
            onClick={() => setFiltersOpen(true)}
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
          >
            <X size={12} />
            Wyczyść
          </button>
        )}
```

na:

```tsx
        {activeFilterCount > 0 && (
          <button
            onClick={clearAdvancedFilters}
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
          >
            <X size={12} />
            Wyczyść
          </button>
        )}
```

- [ ] **Step 3: Dodaj `key` do `FilterPanel`**

Zamień (obecnie ~764–766):

```tsx
      {filtersOpen && (
        <FilterPanel onChange={handleFiltersChange} onCountChange={handleFilterCountChange} allTags={allTags} />
      )}
```

na:

```tsx
      {filtersOpen && (
        <FilterPanel
          key={filterPanelKey}
          onChange={handleFiltersChange}
          onCountChange={handleFilterCountChange}
          allTags={allTags}
        />
      )}
```

- [ ] **Step 4: Sprawdź lint i typy**

Run:
```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Expected: brak nowych błędów.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/receipts/page.tsx
git commit -m "fix(frontend): clear advanced receipt filters from toolbar button"
```

---

### Task 3: Wersjonowanie PATCH + weryfikacja końcowa

**Files:**
- Modify: `frontend/package.json` — `"version": "1.8.3"` → `"1.8.4"`
- Modify: `frontend/package-lock.json` — `"version": "1.8.3"` (root) i `packages[""].version` → `"1.8.4"`

**Interfaces:**
- Consumes: ukończone Taski 1–2.

- [ ] **Step 1: Podbij wersję frontendu**

```json
// frontend/package.json
"version": "1.8.4"
```

W `frontend/package-lock.json` zaktualizuj oba wystąpienia `"version": "1.8.3"` na `"1.8.4"`.

- [ ] **Step 2: Uruchom lint i typy**

Run:
```bash
cd frontend && npx tsc --noEmit && npm run lint
```

Expected: PASS / brak błędów.

- [ ] **Step 3: Weryfikacja manualna (checklista ze spec)**

1. Otwórz `http://localhost:3000/receipts`.
2. Ustaw filtr zaawansowany (np. sklep) → kliknij „Wyczyść" w pasku → lista bez filtra; badge znika; status bez zmian.
3. Otwórz panel filtrów z aktywnymi filtrami → „Wyczyść" w pasku → pola w panelu puste; lista odświeżona.
4. Panel otwarty → „Wyczyść filtry" w panelu → identyczny efekt jak #2.
5. Filtr zaawansowany + status „Do potwierdzenia" → „Wyczyść" → status zostaje; filtry zaawansowane wyczyszczone.
6. Brak filtrów zaawansowanych → przycisk „Wyczyść" niewidoczny.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): bump patch version for receipts clear-filters fix"
```

---

## Self-review (plan vs spec)

| Wymaganie spec | Task |
|----------------|------|
| Toolbar „Wyczyść" czyści filtry zaawansowane | Task 2 |
| `appliedFilters` → EMPTY, count → 0, page → 1 | Task 2 |
| `filterPanelKey` remount panelu | Task 2 |
| Status filter bez zmian | Task 2 (handler nie dotyka `statusFilter`) |
| Usunięcie `onCountChange(0)` przy mount | Task 1 |
| „Wyczyść filtry" w panelu bez zmian | — (istniejący kod) |
| PATCH SemVer FE only | Task 3 |
| Lint + tsc + manualna checklista | Task 1–3 |
| Poza zakresem: sync pól panelu | — (świadomie pominięte) |

Brak placeholderów TBD. Typy i nazwy spójne między taskami.
