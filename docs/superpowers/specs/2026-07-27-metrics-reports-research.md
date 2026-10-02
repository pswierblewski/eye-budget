# Research: Metryki i raporty budżetu domowego

**Data**: 2026-07-27  
**Status**: Research / progress — **nie** zatwierdzony design; kontynuacja w nowej sesji  
**Kontekst**: Po ~pół roku gromadzenia wydatków i przychodów (paragony z kategoriami per wiersz, transakcje bankowe/gotówkowe) celem jest budowa metryk i raportów — iteracyjnie, bez wynajdywania koła na nowo.

---

## 1. Stan repozytorium (stan na 2026-07-27)

### 1.1 Co już istnieje

Feature `001-budget-analysis` oraz UI `/budget` pokrywają m.in.:

| Obszar | Endpointy / UI |
|--------|----------------|
| Podsumowanie miesiąca | `GET /budget/analysis/monthly`, karty na `/budget` |
| Breakdown kategorii + MoM | ten sam endpoint + wykresy |
| Recurring / cyclical | `…/recurring-expenses`, `…/cyclical-alerts` |
| Affordability | `…/affordability` |
| Essential / discretionary | `…/category-classifications` |
| Symulacje + AI narrative | `/budget/simulations`, `…/ai-recommendations` |
| Unified analytics | `GET /transactions/analytics` |
| UI gotowy, niepodpięty | `frontend/components/AnalyticsPanel.tsx` + `getTransactionsAnalytics` |

Szczegóły decyzji algorytmicznych: `docs/superpowers/specs/001-budget-analysis/` (m.in. `research.md`, `spec.md`).

### 1.2 Model danych istotny dla raportów

```text
categories (drzewo parent_id, c_type: expense|income)
vendors / products

receipts_scans ──► receipt_transactions ──► receipt_transaction_items
                         │                    (category_id per pozycja)
                         ├── receipt_bank_links ──► bank_transactions
                         └── receipt_cash_links ──► cash_transactions

bank_transactions
  ├── category_id i/lub bank_transaction_category_splits
  ├── vendor_id, tags[], account_id
  └── settlement_group_members

cash_transactions — analogicznie (bez splits)
```

**Kanoniczne ziarno (grain) dzisiejszych agregatów budżetowych** = wiersz transakcji bankowej / gotówkowej, **nie** pozycja paragonu.

### 1.3 Wymiary i miary dostępne w danych

**Wymiary:** data (`booking_date` / `date`), kategoria (liść + parent), klasyfikacja budżetowa (essential/discretionary), vendor/merchant, tagi, konto bankowe, źródło (bank|cash|receipt), settlement group, splits bankowe, produkt na paragonie.

**Miary już agregowane w kodzie:** expense/income/surplus, count, monthly series, top categories/vendors, MoM %, recurring heurystyki, rolling 3-month averages, per-account totals.

### 1.4 Luki / ograniczenia (ważne przed kolejnymi raportami)

1. Agregaty budżetowe **nie** używają kategorii z pozycji paragonu.
2. `bank_transaction_category_splits` są **ignorowane** przez budget i `/transactions/analytics` (tylko `category_id`).
3. **Dedup niespójny:** unified analytics wyklucza linked cash/receipts; budget SQL `UNION ALL` all bank + all cash → ryzyko double-count.
4. Brak filtrów raportowych: tagi, konto, settlement group, source, rollup parent category.
5. Top-N ograniczone (vendors 10, categories 15); null vendor pomijany.
6. Trend na `/budget` często dostaje **jeden** punkt miesiąca (mimo że `get_monthly_history` istnieje).
7. Uncategorized (`category_id IS NULL`) wypada z breakdownu kategorii (totals nadal je liczą).
8. Brak multi-currency reporting (waluta w danych, analityka zakłada PLN).
9. Settlement groups = operacyjne, nie wymiar raportu.
10. Goals: tabela orphaned po usunięciu feature (nie budować na tym bez reintrodukcji).
11. `AnalyticsPanel` = tani win vs greenfield charts.

### 1.5 Kluczowe ścieżki

- Schema: `backend/migrations/` (m.in. categories, bank, cash, receipts, splits, settlement, budget-*)
- Agregacja: `backend/src/repositories/unified_transactions.py`, `repositories/budget_analysis.py`, `services/budget_analysis.py`
- Kontrakty: `backend/src/data.py`, `main.py`
- FE: `frontend/app/budget/`, `components/budget/*`, `components/AnalyticsPanel.tsx`
- Spec oryginalny: `docs/superpowers/specs/001-budget-analysis/`

---

## 2. Standardy i dobre praktyki (research web, 2026-07-27)

Nie ma jednej normy ISO „raport budżetu domowego”. Są trzy warstwy, które warto rozdzielić.

### 2.1 Dimensional modeling (Kimball) — *jak* modelować

Źródła:

- [Kimball – Grain](https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/grain/)
- [Declaring the Grain](https://www.kimballgroup.com/2003/03/declaring-the-grain/)
- [Microsoft Fabric – Modeling Fact Tables](https://learn.microsoft.com/en-us/fabric/data-warehouse/dimensional-modeling-fact-tables)
- Praktyczne przykłady star schema w personal finance (Power BI / GitHub: fact transactions + dim date/category/account)

**Zasady kluczowe:**

| Zasada | Znaczenie dla eye-budget |
|--------|--------------------------|
| **Declare the grain first** | Jedna definicja: „jeden wiersz = …” zanim budujemy wykresy |
| **Atomic grain** | Najniższy sensowny poziom; rollupy w zapytaniu / API |
| **Nie mieszać ziaren w jednej fact table** | Osobno: transakcja bankowa vs pozycja paragonu |
| **Facts true-to-grain** | Savings rate, MoM %, % kategorii — w warstwie aplikacyjnej, nie w wierszu faktu |
| **Transaction vs periodic snapshot** | Przepływy = suma zdarzeń; saldo konta / net worth = snapshot okresowy |
| **Additive vs semi-additive** | Kwoty PLN są additive; salda i ratio — nie sumować naiwnie w czasie |

Dla skali gospodarstwa domowego (~setki–tysiące tx / pół roku) **nie trzeba** osobnego warehouse’u: wystarczy spójny kontrakt „faktu analitycznego” (SQL view / unified query) + wymiary.

### 2.2 Metody budżetowe — *co* mierzyć / jaki rytuał

| Metoda | Idea | Typowe metryki |
|--------|------|----------------|
| **Cash flow** (Mint → Monarch) | Skąd przyszło → gdzie poszło | income, expense, surplus/net, savings rate |
| **Envelope / zero-based (ZBB)** (YNAB, Goodbudget) | Każdy złoty ma robotę; limity kategorii | budget vs actual, remaining, variance, pace |
| **50/30/20 / needs–wants** | Proporcje potrzeb / zachcianek / oszczędności | % essential vs discretionary (klasyfikacja już w app) |

Źródła m.in.: Fidelity / Monarch o ZBB; przewodniki kategoryzacji (8–12 kategorii głównych); monthly review systems (porównanie do targetów → 1–2 największe odchylenia → jedna decyzja).

### 2.3 Wzorzec raportów w dojrzałych produktach

**Monarch** (Reports / Cash Flow):

- Zakładki: Cash Flow, Spending, Income…
- Dwa tryby: **Breakdown** (totals) vs **Trends** (zmiana w czasie)
- Slice: category / group / merchant; filtry: okres, konta, tagi, kwoty
- Drill-down: klik → lista transakcji
- Sankey (opcjonalnie) dla przepływu income → expenses
- Zapisane widoki raportów

**YNAB**:

- Spending (totals + trends)
- Income vs Expense (tabela miesięczna)
- Net Worth
- Filtry: category groups, timeframe, accounts
- Drill do transakcji

**Wspólny wzorzec produktowy:**

1. Cash flow overview (KPI: income / expense / net / savings rate)
2. Spending explorer (Breakdown **lub** Trends × category/merchant)
3. Income vs expense (miesięczna tabela)
4. Drill-down do transakcji (nie osobny „raport szczegółowy”)
5. Wspólne filtry
6. Dashboard ≠ raporty (dashboard = 3–5 KPI; raporty = slice & dice)

### 2.4 Praktyki UX / jakości danych

- 8–12 kategorii **głównych** w raporcie (u nas: rollup po `parent_id`, nie 40 liści naraz).
- Jedna transakcja → jedna kategoria (lub jawny split); unikać „Miscellaneous” jako śmietnika.
- Transfers między własnymi kontami ≠ income/expense.
- Dane muszą być czyste (dedup, uncategorized) — inaczej wykres kłamie.
- Nie budować 12 wykresów naraz; metryki pod konkretne pytania użytkownika.
- Dashboard: wybierać metryki, które aktualnie poprawiasz; reszta w raportach.

---

## 3. Mapowanie na eye-budget — proponowane iteracje

Kolejność zgodna z Kimballem i ze stanem kodu (od spójnego faktu, nie od galerii wykresów):

| # | Iteracja | Cel | Grain / fokus |
|---|----------|-----|----------------|
| **0** | **Kontrakt faktu** | Jedna definicja: co liczymy; dedup linked bank/cash/receipt; obsługa splits; reguła transfers | bank/cash atomic (+ osobny fact na receipt lines później) |
| **1** | **Cash flow + trends** | Okres, totals, MoM, savings rate; podpięcie `AnalyticsPanel`; wielomiesięczna historia | prawie gotowe w kodzie |
| **2** | **Spending explorer** | Breakdown/Trends × kategoria/vendor + drill do listy tx; filtry | klasyczny produktowy raport |
| **3** | **Budget vs actual** | Limity / envelope (planowanie, nie tylko historia) | wymaga limitów kategorii (goals były usunięte) |
| **4** | **Receipt-line analytics** | „Ile na produkt / kategorię z paragonów” | **osobny grain** — nie mieszać z 1–2 |
| **5** | **Net worth / multi-account depth** | Salda, aktywa | wymaga snapshotów / sald, nie tylko przepływów |

### Najczęstsze pułapki (do uniknięcia)

1. Budować „pełny system raportów” zanim ustali się grain i reguły deduplikacji.
2. Mieszać sumy z pozycji paragonów z sumami bankowymi w jednym wykresie.
3. Ignorować splits i linked transactions — rozjazd z rzeczywistością użytkownika.
4. Traktować net worth jak sumę transakcji (to semi-additive snapshot).

---

## 4. Werdykt sesji research

Tak — istnieją udokumentowane metody; nie trzeba greenfieldu „od wykresów”.

Dla eye-budget najważniejsze:

1. **Kimball grain** — osobno transakcje vs pozycje paragonu.
2. **Cash-flow reports** jak Monarch/YNAB — Breakdown + Trends + drill-down.
3. **Envelope/ZBB** — dopiero gdy potrzebny jest plan (limity), nie sama analiza historii.
4. **Iteracja od spójnego faktu** — potem explorer; receipt-line i net worth później.

Masz już znaczną część warstwy 1–2 w `001-budget-analysis`; największy zysk to **uszpójnienie kontraktu agregacji** i **explorer wydatków**, nie nowy stack analityczny.

---

## 5. Pytanie otwarte (do kontynuacji w nowej sesji)

**Co jest ważniejsze w pierwszej iteracji implementacyjnej?**

- **A)** Uporządkować istniejące raporty cash-flow (dedup, splits, trendy wielomiesięczne, podpięcie AnalyticsPanel)
- **B)** Nowy „explorer” wydatków (kategoria/merchant × breakdown/trends + drill do transakcji)
- **C)** Analityka na poziomie **pozycji paragonu** (unikalna granulacja danych)
- **D)** Budget vs actual / limity kategorii (envelope)

Po wyborze: brainstorm (podejścia → design) → spec w `docs/superpowers/specs/` → plan implementacji.

---

## 6. Linki referencyjne (research)

- Kimball grain: https://www.kimballgroup.com/data-warehouse-business-intelligence-resources/kimball-techniques/dimensional-modeling-techniques/grain/
- Declaring the grain: https://www.kimballgroup.com/2003/03/declaring-the-grain/
- Fabric fact tables: https://learn.microsoft.com/en-us/fabric/data-warehouse/dimensional-modeling-fact-tables/
- Monarch Reports: https://help.monarch.com/hc/en-us/articles/21846787088916-Using-Reports
- Monarch Cash Flow: https://help.monarch.com/hc/en-us/articles/20504904768020-Cash-Flow
- YNAB reports overview: https://www.ynab.com/blog/ynab-reports-and-data
- ZBB (Fidelity): https://www.fidelity.com/learning-center/smart-money/zero-based-budgeting
- Expense dashboard metrics (enterprise, przenaszalne): https://www.drivetrain.ai/post/expense-dashboard
- Kategoryzacja 8–12 kategorii: przykłady w przewodnikach ExpenseKit / Wealthvieu / Innopulse (consumer finance blogs, 2025–2026)

---

## 7. Notatka dla następnej sesji agenta

1. Przeczytać ten plik w całości + `001-budget-analysis/spec.md` i `research.md`.
2. Nie implementować od razu — skill **brainstorming**: pytanie A/B/C/D (lub doprecyzowanie), potem 2–3 podejścia, design, dopiero plan.
3. Przy zmianach kodu: SemVer tylko dla zmienianych stron (FE/BE); UI copy PL; kontrakt API w czterech miejscach.
4. Nie czytać/modyfikować `.env` / sekretów.
