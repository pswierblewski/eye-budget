# Design: AmountInput — globalny separator dziesiętny

Date: 2026-04-15

## Problem

W polskim standardzie (`pl-PL`) separatorem dziesiętnym jest przecinek (`,`), natomiast
JavaScript `parseFloat()` akceptuje wyłącznie kropkę (`.`). Obecne formularze używają
`<input type="number">` + `parseFloat()` bez normalizacji separatora, co powoduje:

- `parseFloat("12,50")` → `12` (obcięcie części dziesiętnej — cichy bug)
- Niespójne zachowanie między przeglądarkami: Chrome z polskim locale OS akceptuje
  przecinek w `type="number"`, Firefox/Safari mogą blokować
- Wyświetlanie przez `.toFixed(2)` daje `"12.50"` zamiast `"12,50"` (niezgodność z `pl-PL`)

## Globalna reguła

| Warstwa | Reguła |
|---|---|
| Separator dziesiętny | Przecinek (`,`) — standard `pl-PL` |
| Wejście (input) | Akceptuj `,` i `.`; normalizuj do `.` wewnętrznie |
| Wyświetlanie | Zawsze `,` via `Intl.NumberFormat("pl-PL")` lub `formatAmount()` |
| Baza danych | `NUMERIC(12,2)` — bez zmian |
| Komponent | **Zawsze `<AmountInput>` dla pól kwotowych; nigdy `<input type="number">`** |

## Rozwiązanie: komponent `AmountInput`

Nowy plik: `frontend/components/ui/AmountInput.tsx`

### Interfejs

```tsx
interface AmountInputProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>,
    'type' | 'value' | 'onChange'> {
  value: number | null;                      // null = puste pole
  onChange: (value: number | null) => void;  // null gdy puste lub nieparsowalne
}
```

### Zachowanie

- Renderuje `<input type="text" inputMode="decimal">` (numeryczna klawiatura na mobile)
- Akceptuje `,` i `.` podczas wpisywania — oba są prawidłowe
- Normalizuje `,` → `.` przed `parseFloat()` wewnętrznie
- Przy mount: inicjalizuje stan wyświetlania jako `"123,50"` (format `pl-PL` bez symbolu
  waluty). Zewnętrzna zmiana propa `value` **nie nadpisuje** tekstu, który użytkownik
  aktualnie edytuje — sync z propem następuje tylko gdy komponent jest nieaktywny (blur)
- `onChange(null)` gdy pole puste lub wpisana wartość nie jest liczbą
- Caller otrzymuje gotowy `number | null` — bez `parseFloat()` po stronie formularza

### Przed i po (przykład GoalForm)

**Przed:**
```tsx
const [amount, setAmount] = useState<string>("");
// submit:
target_amount_pln: parseFloat(amount),

<input
  type="number"
  value={amount}
  onChange={(e) => setAmount(e.target.value)}
/>
```

**Po:**
```tsx
const [amount, setAmount] = useState<number | null>(goal?.target_amount_pln ?? null);
// submit:
target_amount_pln: amount ?? 0,

<AmountInput
  value={amount}
  onChange={setAmount}
/>
```

## Zakres zmian

### Nowy komponent

| Plik | Akcja |
|---|---|
| `frontend/components/ui/AmountInput.tsx` | Nowy komponent |

### Formularze — zamiana inputów na `<AmountInput>`

| Plik | Pola |
|---|---|
| `frontend/components/budget/GoalForm.tsx` | `target_amount_pln`, `monthly_allocation_amount_pln` |
| `frontend/components/budget/SimulationForm.tsx` | `expense_amount` |
| `frontend/components/budget/AffordabilityChecker.tsx` | inputy kwotowe |
| `frontend/components/budget/EmergencyAdvisorPanel.tsx` | inputy kwotowe |
| `frontend/components/BankTransactionSplitEditor.tsx` | kwoty splitów (wiersze) |
| `frontend/app/receipts/[id]/page.tsx` | tylko `editedTotal` |

### Naprawa wyświetlania (`.toFixed(2)` → `formatAmount()`)

| Plik | Lokalizacja | Zmiana |
|---|---|---|
| `frontend/app/receipts/[id]/page.tsx` | sticky bar (linie ~515, 519, 527) | `.toFixed(2)` → `toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })` |

### Bez zmian

- `frontend/app/receipts/[id]/page.tsx` — ceny produktów (`editItemPrice`, `editItemUnitPrice`,
  `editItemQuantity`): mają już ręczną obsługę `replace(",", ".")` i specjalny wzorzec
  edycji (oddzielny `priceInputs` state aby uniknąć resetu kursora). Pozostają bez zmian.
- Backend — bez zmian (`NUMERIC(12,2)` w DB, `float` w Pydantic, `Decimal` w CSV parserze)
- `frontend/components/ui/Amount.tsx` (`formatAmount`) — bez zmian, już poprawny

## Obliczenia w UI

Obliczenia (`reduce`, `Math.abs`, porównania) operują na wartościach `number` — nie są
dotknięte zmianą separatora. `AmountInput` naprawia wyłącznie punkt wejścia do pipeline'u.

## Co to nie obejmuje

- Wielowalutowość — poza zakresem (system jest `PLN`-only)
- Dynamiczne locale — poza zakresem (hardcoded `pl-PL`)
- Formatowanie liczb w nagłówkach analityki — `AnalyticsPanel.tsx` używa już `toLocaleString("pl-PL")`, poprawne
