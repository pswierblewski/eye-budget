# AmountInput — globalny separator dziesiętny — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ujednolicić obsługę separatora dziesiętnego w całym fronendzie — przecinek jako standard `pl-PL`, akceptowane oba (`,` i `.`), parser i komponent w jednym miejscu.

**Architecture:** Nowa czysta funkcja `parseAmountInput` w `lib/amounts.ts` + komponent `AmountInput` opakowujący natywny `<input>` z `twMerge` dla nadpisywania stylów. Wszystkie formularze z kwotami PLN przechodzą na `useState<number | null>` + `<AmountInput>`. Żadnych zmian w backendzie ani w DB.

**Tech Stack:** TypeScript 5, React 18, Next.js 14 App Router, Tailwind CSS, tailwind-merge (już zainstalowane)

---

## File Structure

| Plik | Akcja | Odpowiedzialność |
|---|---|---|
| `frontend/lib/amounts.ts` | Utwórz | Czysta funkcja `parseAmountInput` |
| `frontend/components/ui/AmountInput.tsx` | Utwórz | Komponent inputu z normalizacją separatora |
| `frontend/components/ui/index.ts` | Zmodyfikuj | Eksport `AmountInput` |
| `frontend/components/budget/GoalForm.tsx` | Zmodyfikuj | `targetAmount`, `monthlyAlloc` → `number \| null` |
| `frontend/components/budget/SimulationForm.tsx` | Zmodyfikuj | `amount` → `number \| null` |
| `frontend/components/budget/AffordabilityChecker.tsx` | Zmodyfikuj | `amountStr` → `amount: number \| null` |
| `frontend/components/budget/EmergencyAdvisorPanel.tsx` | Zmodyfikuj | `amountStr` → `amount: number \| null` |
| `frontend/components/BankTransactionSplitEditor.tsx` | Zmodyfikuj | `SplitRow.amount: string` → `number \| null` |
| `frontend/app/receipts/[id]/page.tsx` | Zmodyfikuj | `editedTotal` + naprawa `.toFixed(2)` w sticky barze |

---

## Task 1: Create `parseAmountInput` utility

**Files:**
- Create: `frontend/lib/amounts.ts`

- [ ] **Step 1: Create the file**

```ts
/** Parsuje string kwoty wpisany przez użytkownika.
 *  Akceptuje ',' i '.' jako separator dziesiętny.
 *  Zwraca null gdy wartość pusta lub nieparsowalna. */
export function parseAmountInput(value: string): number | null {
  const normalized = value.trim().replace(",", ".");
  if (normalized === "") return null;
  const n = parseFloat(normalized);
  return isNaN(n) ? null : n;
}
```

- [ ] **Step 2: Verify with lint**

```bash
cd frontend && npm run lint
```

Expected: 0 errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/amounts.ts
git commit -m "feat: add parseAmountInput utility for pl-PL decimal normalization"
```

---

## Task 2: Create `AmountInput` component

**Files:**
- Create: `frontend/components/ui/AmountInput.tsx`
- Modify: `frontend/components/ui/index.ts`

- [ ] **Step 1: Create the component**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { twMerge } from "tailwind-merge";
import { parseAmountInput } from "@/lib/amounts";

interface AmountInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>,
    "type" | "value" | "onChange"> {
  value: number | null;
  onChange: (value: number | null) => void;
}

function formatForInput(value: number): string {
  return value.toFixed(2).replace(".", ",");
}

export function AmountInput({
  value,
  onChange,
  onFocus,
  onBlur,
  className,
  ...props
}: AmountInputProps) {
  const [inputValue, setInputValue] = useState<string>(
    value !== null ? formatForInput(value) : ""
  );
  const focused = useRef(false);

  useEffect(() => {
    if (!focused.current) {
      setInputValue(value !== null ? formatForInput(value) : "");
    }
  }, [value]);

  return (
    <input
      {...props}
      type="text"
      inputMode="decimal"
      className={twMerge(
        "border border-gray-200 rounded-md bg-white focus:outline-none focus:ring-2 focus:ring-accent/30 focus:border-accent transition-colors text-sm px-3 py-1.5",
        className
      )}
      value={inputValue}
      onFocus={(e) => {
        focused.current = true;
        onFocus?.(e);
      }}
      onBlur={(e) => {
        focused.current = false;
        setInputValue(value !== null ? formatForInput(value) : "");
        onBlur?.(e);
      }}
      onChange={(e) => {
        const raw = e.target.value;
        setInputValue(raw);
        onChange(parseAmountInput(raw));
      }}
    />
  );
}
```

- [ ] **Step 2: Export from `frontend/components/ui/index.ts`**

Dodaj na końcu pliku:

```ts
export { AmountInput } from "./AmountInput";
```

- [ ] **Step 3: Verify with lint**

```bash
cd frontend && npm run lint
```

Expected: 0 errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/ui/AmountInput.tsx frontend/components/ui/index.ts
git commit -m "feat: add AmountInput component with pl-PL decimal normalization"
```

---

## Task 3: Update GoalForm

**Files:**
- Modify: `frontend/components/budget/GoalForm.tsx:1-120`

- [ ] **Step 1: Replace amount state and import**

W sekcji importów (linia 1–8) dodaj `AmountInput` do importu z `@/components/ui`:

```ts
import { Input, Button, DateInput, Tooltip, AmountInput } from "@/components/ui";
```

Zmień linie 20–25:

```ts
const [targetAmount, setTargetAmount] = useState<number | null>(
  goal?.target_amount_pln ?? null
);
const [monthlyAlloc, setMonthlyAlloc] = useState<number | null>(
  goal?.monthly_allocation_amount_pln ?? null
);
```

- [ ] **Step 2: Update mutationFn (linie 35–38)**

```ts
target_amount_pln: targetAmount ?? 0,
monthly_allocation_amount_pln: monthlyAlloc ?? 0,
```

- [ ] **Step 3: Update canSubmit (linie 49–52)**

```ts
const canSubmit =
  name.trim() !== "" &&
  targetAmount !== null &&
  targetAmount > 0;
```

- [ ] **Step 4: Replace targetAmount input (linie 66–71)**

```tsx
<AmountInput
  value={targetAmount}
  onChange={setTargetAmount}
  placeholder="10000"
/>
```

- [ ] **Step 5: Replace monthlyAlloc input (linie 77–82)**

```tsx
<AmountInput
  value={monthlyAlloc}
  onChange={setMonthlyAlloc}
  placeholder="500"
/>
```

- [ ] **Step 6: Verify with lint**

```bash
cd frontend && npm run lint
```

Expected: 0 errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/budget/GoalForm.tsx
git commit -m "feat: replace amount inputs in GoalForm with AmountInput"
```

---

## Task 4: Update SimulationForm

**Files:**
- Modify: `frontend/components/budget/SimulationForm.tsx:1-106`

- [ ] **Step 1: Replace amount state and import**

W sekcji importów (linia 6) dodaj `AmountInput`:

```ts
import { Input, Button, DateInput, AmountInput } from "@/components/ui";
```

Zmień linię 18:

```ts
const [amount, setAmount] = useState<number | null>(null);
```

- [ ] **Step 2: Update mutationFn (linia 27)**

```ts
expense_amount_pln: amount ?? 0,
```

- [ ] **Step 3: Update canSubmit (linie 37–42)**

```ts
const canSubmit =
  name.trim() !== "" &&
  expenseName.trim() !== "" &&
  amount !== null &&
  amount > 0 &&
  startDate !== "";
```

- [ ] **Step 4: Replace amount input (linie 64–69)**

```tsx
<AmountInput
  value={amount}
  onChange={setAmount}
  placeholder="20000"
/>
```

- [ ] **Step 5: Verify with lint**

```bash
cd frontend && npm run lint
```

Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/budget/SimulationForm.tsx
git commit -m "feat: replace amount input in SimulationForm with AmountInput"
```

---

## Task 5: Update AffordabilityChecker

**Files:**
- Modify: `frontend/components/budget/AffordabilityChecker.tsx:1-108`

- [ ] **Step 1: Replace amount state and import**

W sekcji importów (linia 6) zastąp `Input` → dodaj `AmountInput` (zostaw `Input` bo nie jest tu używany — usuń jeśli nie ma innych użyć; sprawdź):

Linia 6 staje się:
```ts
import { AmountInput, Button, Amount } from "@/components/ui";
```

(Oryginalnie: `import { Input, Button, Amount } from "@/components/ui"` — `Input` nie jest używany poza inputem kwoty, więc usuń go.)

Zmień linię 32:

```ts
const [amount, setAmount] = useState<number | null>(null);
```

- [ ] **Step 2: Update mutationFn (linia 36)**

```ts
mutationFn: () => checkAffordability(amount!),
```

- [ ] **Step 3: Update canSubmit (linie 40–41)**

Usuń zmienną `amount` (linia 40, bo mamy już `amount` ze stanu) i zaktualizuj `canSubmit`:

```ts
const canSubmit = amount !== null && amount > 0;
```

- [ ] **Step 4: Replace amount input (linie 48–54)**

```tsx
<AmountInput
  value={amount}
  onChange={setAmount}
  placeholder="Kwota w PLN"
  className="max-w-[160px]"
/>
```

- [ ] **Step 5: Verify with lint**

```bash
cd frontend && npm run lint
```

Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/budget/AffordabilityChecker.tsx
git commit -m "feat: replace amount input in AffordabilityChecker with AmountInput"
```

---

## Task 6: Update EmergencyAdvisorPanel

**Files:**
- Modify: `frontend/components/budget/EmergencyAdvisorPanel.tsx:1-129`

- [ ] **Step 1: Replace amount state and import**

Linia 6 — zastąp `Input` → `AmountInput` (sprawdź czy `Input` jest używany dla pola `description`; tak jest — zostaw `Input`):

```ts
import { Input, AmountInput, Button, Amount } from "@/components/ui";
```

Zmień linię 11:

```ts
const [amount, setAmount] = useState<number | null>(null);
```

- [ ] **Step 2: Update mutationFn (linie 16–17)**

```ts
mutationFn: () =>
  getEmergencyAdvice(amount!, description || undefined),
```

- [ ] **Step 3: Update canSubmit (linie 21–22)**

Usuń linię `const amount = parseFloat(amountStr);` i zaktualizuj `canSubmit`:

```ts
const canSubmit = amount !== null && amount > 0;
```

- [ ] **Step 4: Replace amount input (linie 27–33)**

```tsx
<AmountInput
  value={amount}
  onChange={setAmount}
  placeholder="Kwota wydatku (PLN)"
  className="max-w-[160px]"
/>
```

- [ ] **Step 5: Verify with lint**

```bash
cd frontend && npm run lint
```

Expected: 0 errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/budget/EmergencyAdvisorPanel.tsx
git commit -m "feat: replace amount input in EmergencyAdvisorPanel with AmountInput"
```

---

## Task 7: Update BankTransactionSplitEditor

**Files:**
- Modify: `frontend/components/BankTransactionSplitEditor.tsx:1-233`

- [ ] **Step 1: Add AmountInput import**

Linia 7 — dodaj `AmountInput` do importu z `@/components/ui`:

```ts
import { AmountInput } from "@/components/ui";
```

- [ ] **Step 2: Change SplitRow type (linie 10–14)**

```ts
interface SplitRow {
  id: number;
  category_id: number | null;
  amount: number | null;
}
```

- [ ] **Step 3: Update `initRows` (linie 23–35)**

```ts
function initRows(splits: BankTransactionSplit[] | null | undefined, nextId: () => number): SplitRow[] {
  if (splits && splits.length > 0) {
    return splits.map((s) => ({
      id: nextId(),
      category_id: s.category_id,
      amount: s.amount,
    }));
  }
  return [
    { id: nextId(), category_id: null, amount: null },
    { id: nextId(), category_id: null, amount: null },
  ];
}
```

- [ ] **Step 4: Update `updateAmount` signature (linie 59–63)**

```ts
function updateAmount(index: number, amount: number | null) {
  setRows((prev) =>
    prev.map((row, i) => (i === index ? { ...row, amount } : row))
  );
}
```

- [ ] **Step 5: Update `addRow` (linia 66)**

```ts
function addRow() {
  setRows((prev) => [...prev, { id: nextRowId(), category_id: null, amount: null }]);
}
```

- [ ] **Step 6: Update `validate` (linie 73–97)**

```ts
function validate(): string | null {
  if (rows.length < 2) {
    return "Podział musi zawierać co najmniej 2 wiersze.";
  }
  for (let i = 0; i < rows.length; i++) {
    if (rows[i].category_id === null) {
      return `Wiersz ${i + 1}: wybierz kategorię.`;
    }
    const val = rows[i].amount;
    if (val === null || val <= 0) {
      return `Wiersz ${i + 1}: podaj prawidłową kwotę (liczba dodatnia).`;
    }
  }
  const sumCents = rows.reduce(
    (acc, r) => acc + Math.round((r.amount ?? 0) * 100),
    0
  );
  const expectedCents = Math.round(txAmount * 100);
  if (sumCents !== expectedCents) {
    const sumDisplay = (sumCents / 100).toFixed(2);
    const expectedDisplay = (expectedCents / 100).toFixed(2);
    return `Suma kwot (${sumDisplay} PLN) musi być równa kwocie transakcji (${expectedDisplay} PLN).`;
  }
  return null;
}
```

- [ ] **Step 7: Update `handleSave` payload (linie 108–113)**

```ts
rows.map((r) => {
  if (r.category_id === null) throw new Error("Unexpected null category_id after validation");
  return { category_id: r.category_id, amount: r.amount! };
})
```

- [ ] **Step 8: Replace amount input in JSX (linie 156–166)**

```tsx
<AmountInput
  value={row.amount}
  onChange={(v) => updateAmount(i, v)}
  placeholder="0,00"
  className="w-full text-sm border border-indigo-200 rounded-md px-2 py-1 bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-[#635bff] text-gray-900 mt-1"
/>
```

Usuń też atrybuty `step` i `min` — nie dotyczą `type="text"`.

- [ ] **Step 9: Verify with lint**

```bash
cd frontend && npm run lint
```

Expected: 0 errors.

- [ ] **Step 10: Commit**

```bash
git add frontend/components/BankTransactionSplitEditor.tsx
git commit -m "feat: replace split amount inputs in BankTransactionSplitEditor with AmountInput"
```

---

## Task 8: Update `receipts/[id]/page.tsx`

**Files:**
- Modify: `frontend/app/receipts/[id]/page.tsx`

- [ ] **Step 1: Add AmountInput and formatAmount to imports**

Linia 10 — dodaj `AmountInput` i `formatAmount` do importu z `@/components/ui`:

```ts
import { StatusBadge, NavLink, Button, ConfirmDeleteModal, PrevNextNav, SectionLabel, Card, ThreeDotsMenu, DateInput, AmountInput, formatAmount } from "@/components/ui";
```

- [ ] **Step 2: Change editedTotal state type (linia 74)**

```ts
const [editedTotal, setEditedTotal] = useState<number | null>(null);
```

- [ ] **Step 3: Fix editedTotal initialization in useEffect (linia 151)**

```ts
setEditedTotal(scan.result.total);
```

(Usuń `.toFixed(2)` — teraz to liczba, nie string.)

- [ ] **Step 4: Update parsedTotal calculation (linia 383)**

```ts
const parsedTotal = editedTotal ?? 0;
```

(Usuń `parseFloat(editedTotal) || 0`.)

- [ ] **Step 5: Update submit handler (linia 174)**

```ts
total: editedTotal ?? undefined,
```

(Usuń `editedTotal ? parseFloat(editedTotal) : undefined`.)

- [ ] **Step 6: Replace editedTotal input (linie 1137–1143)**

```tsx
<AmountInput
  value={editedTotal}
  onChange={setEditedTotal}
  className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
/>
```

- [ ] **Step 7: Fix sticky bar display — Paragon i Produkty (linie ~515, 519)**

Zastąp:
```tsx
<span className="font-semibold text-gray-900">{stickyTotal.toFixed(2)} PLN</span>
```
na:
```tsx
<span className="font-semibold text-gray-900">{formatAmount(stickyTotal)}</span>
```

Zastąp:
```tsx
<span className="font-semibold text-gray-900">{stickyCalc.toFixed(2)} PLN</span>
```
na:
```tsx
<span className="font-semibold text-gray-900">{formatAmount(stickyCalc)}</span>
```

- [ ] **Step 8: Fix sticky bar display — różnica (linia ~527)**

Zastąp:
```tsx
różnica {stickyDiff > 0 ? "+" : ""}{stickyDiff.toFixed(2)} PLN
```
na:
```tsx
różnica {stickyDiff > 0 ? "+" : ""}{stickyDiff.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN
```

- [ ] **Step 9: Verify with lint**

```bash
cd frontend && npm run lint
```

Expected: 0 errors.

- [ ] **Step 10: Manual smoke test**

```bash
cd frontend && npm run dev
```

Przetestuj:
1. Otwórz dowolny paragon — wpisz kwotę z przecinkiem (`12,50`) w polu "Z paragonu" → liczby w sticky barze powinny pokazać `12,50 PLN`
2. Wpisz kwotę z kropką (`12.50`) → ten sam efekt
3. Sprawdź, że sticky bar wyświetla `12,50 PLN` zamiast `12.50 PLN`
4. Otwórz cel finansowy (Goals) → wpisz kwotę z przecinkiem → zapisz → sprawdź że się zapisało poprawnie
5. Otwórz podział transakcji bankowej → wpisz kwoty z przecinkami → walidacja sumy powinna działać

- [ ] **Step 11: Commit**

```bash
git add frontend/app/receipts/\[id\]/page.tsx
git commit -m "feat: fix editedTotal AmountInput + pl-PL display in sticky bar"
```

---

## Self-Review

**Spec coverage:**
- ✅ Reguła globalna udokumentowana (w spec.md)
- ✅ `parseAmountInput` — Task 1
- ✅ `AmountInput` komponent — Task 2
- ✅ GoalForm — Task 3
- ✅ SimulationForm — Task 4
- ✅ AffordabilityChecker — Task 5
- ✅ EmergencyAdvisorPanel — Task 6
- ✅ BankTransactionSplitEditor — Task 7
- ✅ receipts/[id]/page.tsx `editedTotal` — Task 8
- ✅ receipts/[id]/page.tsx `.toFixed(2)` sticky bar — Task 8
- ✅ Ceny produktów w receipts NIE zmieniane (zgodnie ze spec — mają własny pattern)

**Placeholder scan:** Brak TBD/TODO.

**Type consistency:**
- `parseAmountInput(value: string): number | null` — używane spójnie w `AmountInput` (Task 2) i opisane w Tasks 3–8
- `SplitRow.amount: number | null` — zdefiniowane w Task 7 Step 2, używane w Steps 4–7
- `updateAmount(index: number, amount: number | null)` — zdefiniowane w Step 4, wywoływane w Step 8 jako `(v) => updateAmount(i, v)`
