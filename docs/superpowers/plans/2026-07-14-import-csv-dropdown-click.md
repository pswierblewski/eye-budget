# Import CSV — lista kont otwierana klikiem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Zmienić mechanizm otwierania listy kont w przycisku „Import CSV” na `/bank-transactions` z CSS hover (`group-hover`) na klik, żeby przerwa (`mt-1`) między przyciskiem i listą nie powodowała zamykania listy przed kliknięciem elementu.

**Architecture:** Lokalny `useState` (`importMenuOpen`) + jeden `useRef` na wrapper obejmujący przycisk i listę + `useEffect` z listenerem `mousedown` na `document`, który zamyka listę po kliknięciu poza wrapperem — ten sam mechanizm już używany w `components/ui/ThreeDotsMenu.tsx`. Bez portalu/`fixed` positioning (niepotrzebne w nagłówku strony). Dodatkowo mały `ChevronDown` (lucide-react) obok etykiety, obracany o 180° gdy menu otwarte.

**Tech Stack:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, lucide-react. Brak nowych zależności.

**Uwaga o testach:** Ta strona (`frontend/app/bank-transactions/page.tsx`) nie ma dziś żadnych testów komponentowych (RTL/Playwright) — jedyne testy frontendowe w repo to testy czystej logiki (`*.test.ts`, Vitest). Pisanie pierwszego w repo testu komponentowego dla całej strony (z jej ~15 zależnościami: react-query, Pusher, modale, DataTable) tylko żeby przetestować toggle jednego dropdownu byłoby nieproporcjonalne i niekonsystentne z resztą kodu — decyzja ta była częścią zatwierdzonego spec (`docs/superpowers/specs/2026-07-14-import-csv-dropdown-click-design.md`). Weryfikacja: `tsc --noEmit`, `npm run lint`, manualna checklista w przeglądarce (Task 4).

---

### Task 1: Stan otwarcia menu + ref + zamykanie po kliknięciu poza obszarem

**Files:**
- Modify: `frontend/app/bank-transactions/page.tsx:427-430` (blok stanu), `frontend/app/bank-transactions/page.tsx:447-453` (obok istniejących `useEffect`)

- [ ] **Step 1: Dodaj stan `importMenuOpen` i ref `importMenuRef`**

Znajdź istniejący blok (obecnie linie 427-430):

```typescript
  const accountFileRef = useRef<HTMLInputElement>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<number | undefined>(undefined);
  const [showAccountsModal, setShowAccountsModal] = useState(false);
  const [pendingImportAccountId, setPendingImportAccountId] = useState<number | undefined>(undefined);
```

Zamień na:

```typescript
  const accountFileRef = useRef<HTMLInputElement>(null);
  const [selectedAccountId, setSelectedAccountId] = useState<number | undefined>(undefined);
  const [showAccountsModal, setShowAccountsModal] = useState(false);
  const [pendingImportAccountId, setPendingImportAccountId] = useState<number | undefined>(undefined);
  const [importMenuOpen, setImportMenuOpen] = useState(false);
  const importMenuRef = useRef<HTMLDivElement>(null);
```

- [ ] **Step 2: Dodaj `useEffect` zamykający menu po kliknięciu poza wrapperem**

Znajdź istniejący blok cleanup Pushera (obecnie linie 447-453):

```typescript
  // Cleanup Pusher on unmount
  useEffect(() => {
    return () => {
      channelRef.current?.unsubscribe();
      channelRef.current = null;
    };
  }, []);
```

Zaraz po nim (przed kolejnym istniejącym `useEffect` z `ensureBankTransactionsChannel`) dodaj nowy blok:

```typescript
  // Close the "Import CSV" account menu when clicking outside of it
  useEffect(() => {
    if (!importMenuOpen) return;
    const onDocumentMouseDown = (e: MouseEvent) => {
      if (importMenuRef.current?.contains(e.target as Node)) return;
      setImportMenuOpen(false);
    };
    document.addEventListener("mousedown", onDocumentMouseDown);
    return () => document.removeEventListener("mousedown", onDocumentMouseDown);
  }, [importMenuOpen]);
```

- [ ] **Step 3: Sprawdź typy**

Run: `cd frontend && npx tsc --noEmit`
Expected: brak nowych błędów (plik się jeszcze kompiluje — JSX używający `importMenuOpen`/`importMenuRef` dodajemy w Task 3, więc `importMenuRef`/`setImportMenuOpen` na tym etapie mogą być zgłoszone jako nieużywane zmienne przez lint, nie przez `tsc`; to naprawi się w Task 3).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/bank-transactions/page.tsx
git commit -m "feat(frontend): add click-toggle state for import CSV account menu"
```

---

### Task 2: `handleImportClick` zamyka menu przy wyborze konta

**Files:**
- Modify: `frontend/app/bank-transactions/page.tsx:620-623`

- [ ] **Step 1: Zaktualizuj `handleImportClick`**

Znajdź:

```typescript
  function handleImportClick(accountId: number) {
    setPendingImportAccountId(accountId);
    accountFileRef.current?.click();
  }
```

Zamień na:

```typescript
  function handleImportClick(accountId: number) {
    setImportMenuOpen(false);
    setPendingImportAccountId(accountId);
    accountFileRef.current?.click();
  }
```

- [ ] **Step 2: Sprawdź typy**

Run: `cd frontend && npx tsc --noEmit`
Expected: brak błędów.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/bank-transactions/page.tsx
git commit -m "feat(frontend): close import CSV menu when an account is selected"
```

---

### Task 3: JSX — klik zamiast hover, chevron, wrapper ref

**Files:**
- Modify: `frontend/app/bank-transactions/page.tsx:37` (import ikony), `frontend/app/bank-transactions/page.tsx:893-914` (blok dropdownu)

- [ ] **Step 1: Dodaj `ChevronDown` do importu ikon**

Znajdź (obecnie linia 37):

```typescript
import { Upload, ArrowRight, RefreshCw, Link2, Settings } from "lucide-react";
```

Zamień na:

```typescript
import { Upload, ArrowRight, RefreshCw, Link2, Settings, ChevronDown } from "lucide-react";
```

- [ ] **Step 2: Zamień blok dropdownu z hover na klik**

Znajdź (obecnie linie 893-914):

```typescript
          {accountsQuery.data && accountsQuery.data.length > 0 ? (
            <div className="relative group">
              <Button
                variant="primary"
                size="md"
                disabled={importMutation.isPending}
              >
                <Upload className="h-4 w-4 mr-2" />
                Import CSV
              </Button>
              <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 hidden group-hover:block min-w-[180px]">
                {accountsQuery.data.map((acc: BankAccountStats) => (
                  <button
                    key={acc.id}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg"
                    onClick={() => handleImportClick(acc.id)}
                  >
                    {acc.name}
                  </button>
                ))}
              </div>
            </div>
          ) : (
```

Zamień na:

```typescript
          {accountsQuery.data && accountsQuery.data.length > 0 ? (
            <div className="relative" ref={importMenuRef}>
              <Button
                variant="primary"
                size="md"
                disabled={importMutation.isPending}
                onClick={() => setImportMenuOpen((v) => !v)}
              >
                <Upload className="h-4 w-4 mr-2" />
                Import CSV
                <ChevronDown
                  className={`h-4 w-4 ml-1 transition-transform ${importMenuOpen ? "rotate-180" : ""}`}
                />
              </Button>
              {importMenuOpen && (
                <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-[180px]">
                  {accountsQuery.data.map((acc: BankAccountStats) => (
                    <button
                      key={acc.id}
                      className="w-full text-left px-3 py-2 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg"
                      onClick={() => handleImportClick(acc.id)}
                    >
                      {acc.name}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
```

- [ ] **Step 3: Sprawdź typy i lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: brak błędów.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/bank-transactions/page.tsx
git commit -m "fix(frontend): open import CSV account menu on click instead of hover"
```

---

### Task 4: Weryfikacja manualna w przeglądarce

**Files:** brak zmian kodu — tylko weryfikacja.

- [ ] **Step 1: Uruchom frontend lokalnie**

Run: `cd frontend && npm run dev`
Otwórz `http://localhost:3000/bank-transactions` (backend musi działać — patrz `backend/AGENTS.md`, `uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload`).

- [ ] **Step 2: Sprawdź checklistę**

Zweryfikuj każdy punkt:
- [ ] Klik na „Import CSV” otwiera listę kont; chevron obraca się o 180°.
- [ ] Przesunięcie kursora z przycisku do listy (przez odstęp `mt-1`) **nie** zamyka listy.
- [ ] Klik na nazwę konta na liście: lista się zamyka, otwiera się systemowy file picker (import działa jak dotychczas).
- [ ] Klik na przycisk „Import CSV” drugi raz (gdy lista otwarta) zamyka listę.
- [ ] Klik gdziekolwiek poza przyciskiem i listą (np. w tabeli transakcji) zamyka listę.
- [ ] Gdy trwa import (`importMutation.isPending`) przycisk jest wyszarzony i nieklikalny — lista się nie otwiera.
- [ ] Jeśli nie ma żadnego konta, przycisk „Import CSV” jest `disabled` z tooltipem „Najpierw dodaj konto bankowe” (branch bez zmian — sanity check, że nic nie popsuliśmy).

- [ ] **Step 3: Zaktualizuj CHANGELOG / wersję (jeśli wymagane przez `frontend/AGENTS.md`)**

Zgodnie z `frontend/AGENTS.md` (SemVer, tylko FE): to PATCH (poprawka błędu UI, brak nowej funkcjonalności). Podbij `"version"` w `frontend/package.json` i `package-lock.json` (root + `packages[""].version`) o jeden PATCH.

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore(frontend): bump version for import CSV dropdown click fix"
```

---

## Self-Review (wypełnione podczas pisania planu)

1. **Spec coverage:** wszystkie 7 punktów „Zachowanie docelowe” ze spec pokryte: (1) toggle klikiem — Task 3; (2) brak zamykania przy ruchu kursora — wynika z usunięcia `group-hover` w Task 3; (3) klik na konto zamyka + importuje — Task 2; (4) klik poza obszarem zamyka — Task 1 Step 2; (5) chevron z obrotem — Task 3; (6) branch bez kont bez zmian — nietknięty, zweryfikowany w Task 4 checklist; (7) `disabled` podczas importu bez zmian — nietknięty (istniejący prop `disabled={importMutation.isPending}` zachowany w Task 3).
2. **Placeholder scan:** brak „TBD”/„dodaj obsługę błędów” — każdy krok ma pełny kod.
3. **Type consistency:** `importMenuOpen` / `setImportMenuOpen` / `importMenuRef` nazwane konsekwentnie we wszystkich trzech zadaniach; brak rozjazdów nazw.
