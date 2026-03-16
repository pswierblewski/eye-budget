# Feature Specification: Budget Analysis & Insights

**Feature Branch**: `001-budget-analysis`  
**Created**: 2026-03-13  
**Status**: Draft  
**Input**: User description: "budget-analysis: chcę mieć narzędzie do analizy moich wydatków."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Monthly Spending Overview (Priority: P1)

As a household budget manager, I want to see a clear monthly breakdown of my spending across all categories so I can quickly understand where my money went in any given month and compare it to previous months.

**Why this priority**: This is the foundational analysis layer. Without knowing current monthly spending totals by category, no other financial insight is actionable. All higher-priority stories build on this data. Delivers immediate, standalone value from day one.

**Independent Test**: Can be fully tested by navigating to the analysis section, selecting a month with existing transactions, and verifying category-level totals, percentages, and month-over-month changes are displayed correctly.

**Acceptance Scenarios**:

1. **Given** I have transactions recorded for a month, **When** I open the monthly analysis view, **Then** I see total spending grouped by category with amounts and percentage of total budget
2. **Given** I select a specific month, **When** the analysis loads, **Then** I see the change vs. the previous month (absolute and relative) per category
3. **Given** multiple months of data exist, **When** I view the spending trend chart, **Then** I can see month-over-month total spending evolution across a selectable time range

---

### User Story 2 - Recurring & Cyclical Expense Tracker (Priority: P2)

As a user with fixed monthly obligations and irregular large annual expenses (car insurance ~3,000 PLN, Christmas presents, vacations), I want to see my recurring expenses separated from variable spending so I can plan ahead and ensure funds are available when needed.

**Why this priority**: Cyclical expenses are a major source of financial stress when they appear unexpectedly. Identifying them proactively enables planning. Builds directly on Story 1 data.

**Independent Test**: Can be tested by verifying that recurring expenses detected from transaction history appear in a dedicated section with frequency, average amount, and next expected occurrence date.

**Acceptance Scenarios**:

1. **Given** I have recurring monthly expenses (mortgage, subscriptions), **When** I open the recurring expenses view, **Then** I see each listed with frequency, average amount, and last occurrence
2. **Given** I have an annual expense (e.g., car insurance) in my history, **When** I view cyclical expenses, **Then** I see it with an estimated next occurrence date and approximate expected amount
3. **Given** a large cyclical expense is within 90 days, **When** I view the analysis dashboard, **Then** I see a prominent alert indicating the upcoming obligation and its estimated amount

---

### User Story 3 - "Can I Afford It?" Affordability Check (Priority: P3)

As a user considering a purchase, I want to quickly understand whether buying something aligns with my current financial situation and active goals so I can make informed decisions (e.g., "I have 20,000 PLN, should I buy 500 PLN shoes right now?").

**Why this priority**: Directly addresses the user's stated core question "czy mnie stać" (can I afford it) — not just technically, but strategically. Translates raw data into a clear yes/contextual-recommendation.

**Independent Test**: Can be tested by entering a purchase amount and verifying the system returns a recommendation based on current available funds, upcoming obligations within 30 days, and active financial goals.

**Acceptance Scenarios**:

1. **Given** I have 20,000 PLN and want to spend 500 PLN on shoes, **When** I run an affordability check, **Then** I see both "technically affordable: yes" and a strategic recommendation based on active financial focus and upcoming expenses
2. **Given** I have an active financial focus (mortgage overpayment), **When** I check affordability of a discretionary purchase, **Then** I see the impact on that goal and how much I'd be redirecting away from it
3. **Given** I have a large upcoming expense (e.g., car insurance) within 30 days, **When** I run an affordability check, **Then** I see a warning that the discretionary purchase may conflict with the upcoming obligation

---

### User Story 4 - Budget Simulation (Priority: P4)

As a user considering a significant purchase or financial commitment (e.g., new windows for 20,000 PLN, a car, recurring house construction costs), I want to run a simulation showing how that expense would affect my monthly budget, goal timelines, and financial plans over the coming months, so I can make an informed decision and plan the timing or necessary adjustments before committing.

**Why this priority**: The user explicitly needs to answer complex forward-looking questions: "how do I prepare financially for building a house?", "can I afford new windows this year without derailing my mortgage overpayment goal?". A simulation transforms current budget data into a projected future, enabling the user to see consequences before spending — not after.

**Independent Test**: Can be tested by entering a hypothetical large expense (name, amount, type: one-time or recurring, timing), and verifying the system returns a multi-month surplus projection, per-goal impact (updated completion dates), and AI-generated adjustment suggestions — all within one view.

**Acceptance Scenarios**:

1. **Given** I enter a one-time expense of 20,000 PLN (new windows) in month 3, **When** I run the simulation, **Then** I see a month-by-month projection of my monthly surplus over the next 12 months with and without this expense side-by-side
2. **Given** the simulation runs against my active goals, **When** results are shown, **Then** I see each goal's projected completion date updated to reflect the expense impact (e.g., "house construction fund: delayed by 3 months")
3. **Given** the simulation shows a negative impact on my goals, **When** viewing results, **Then** I see AI-generated suggestions for how to offset the impact (e.g., "pause goal X for 2 months", "reduce dining-out by 400 PLN/month for 3 months")
4. **Given** I want to model a recurring commitment (e.g., +2,000 PLN/month for future house construction loan repayment), **When** I run the simulation, **Then** I see the long-term projected impact on my financial focus and all goal timelines across at least 24 months
5. **Given** I have completed a simulation, **When** viewing results, **Then** I can save the scenario under a name for future reference and comparison with other scenarios

---

### User Story 5 - Purchase Planning & Goal Setting (Priority: P5)

As a user planning future purchases and events (vacation, house construction down payment, large gifts), I want to set financial goals with target amounts and dates so I can track saving progress and know exactly how much to set aside each month.

**Why this priority**: Translates financial awareness into forward-looking action. Important but requires Stories 1–3 to deliver full value, since goal recommendations are driven by current spending analysis.

**Independent Test**: Can be tested by creating a goal (e.g., "Mountain trip - 3,000 PLN in 4 months"), verifying the system shows required monthly savings, feasibility based on current spending, and progress tracking.

**Acceptance Scenarios**:

1. **Given** I create a goal "Mountain trip" with 3,000 PLN target in 4 months, **When** I view goals, **Then** I see the required monthly savings, whether my current budget allows it, and which spending categories to reduce if needed
2. **Given** I have multiple active goals simultaneously, **When** I view the goals overview, **Then** I see a prioritized allocation recommendation showing how to split available savings across all goals
3. **Given** I achieve a goal and make the purchase, **When** I log the transaction, **Then** I can link it to the completed goal for historical tracking

---

### User Story 6 - Emergency Expense Management (Priority: P6)

As a user facing an unexpected large expense (broken laptop, urgent home repair), I want to quickly understand which spending I can cut or defer to absorb the cost without derailing my financial plan and goals.

**Why this priority**: Addresses the user's stated anxiety about unexpected expenses and "always something at the cost of something else." Requires Story 1's discretionary/essential expense classification to work.

**Independent Test**: Can be tested by entering an emergency expense amount and verifying the system suggests specific budget categories to reduce and their available amounts, plus the impact on existing goals.

**Acceptance Scenarios**:

1. **Given** I need 4,000 PLN urgently for a new laptop, **When** I use the emergency expense advisor, **Then** I see a list of discretionary spending categories I could reduce and how much each contributes toward covering the cost
2. **Given** I have active savings goals, **When** an emergency amount is entered, **Then** I see the impact on each goal and which one(s) to pause temporarily with a recovery timeline
3. **Given** the emergency cannot be fully covered by discretionary cuts alone, **When** I view options, **Then** I see the minimum monthly budget impact and how many months it would take to recover financially

---

### Edge Cases

- What happens when there is less than 1 month of transaction data? Analysis should degrade gracefully with a clear message explaining minimum data requirements for each insight type (e.g., simulation requires at least 1 month of baseline data; passive AI recommendations require 3 months).
- What happens when a simulation is run with no active financial goals? The simulation still shows the surplus projection; the goal-impact section is hidden with a prompt to create goals.
- How does the system handle a month with zero transactions in a specific category? Category should still be visible (with zero) in historical comparisons to avoid misleading trend lines.
- What if cyclical expense amounts vary significantly year-over-year (e.g., vacation costs differ 3×)? Show a range (min–max from history) rather than a single figure.
- What if a user has no stated financial goals or active focus? Affordability checks should still work using general savings rate best practices as a baseline.
- What happens when income transactions are missing for a given month (e.g., no tagged income in that period)? The system should display a warning that surplus cannot be calculated for that month and flag it visually, rather than silently showing incorrect data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST display monthly spending totals grouped by category for any selected month with available transaction data
- **FR-002**: System MUST show month-over-month spending change (absolute amount and percentage) per category
- **FR-003**: System MUST display a multi-month spending trend chart with selectable time range
- **FR-004**: System MUST automatically detect and display recurring monthly expenses from transaction history, showing frequency and average amount
- **FR-005**: System MUST automatically detect and display cyclical annual expenses from transaction history, with estimated next occurrence date and expected amount range
- **FR-006**: System MUST alert the user when a large cyclical expense (above a configurable threshold) is within 90 days
- **FR-007**: System MUST auto-classify all spending categories into "essential/fixed" or "discretionary/variable" based on category type, and MUST allow the user to override the classification per category (not per individual transaction)
- **FR-008**: System MUST provide an affordability check for a user-entered purchase amount, evaluating it against: current available balance, upcoming obligations within 30 days, and active financial goals
- **FR-009**: System MUST display the user's current financial focus prominently so it influences affordability checks, simulation results, and AI recommendations
- **FR-010**: System MUST provide a Budget Simulation tool allowing the user to enter a hypothetical expense with: name, amount, type (one-time or recurring), and start date
- **FR-010b**: The simulation MUST produce a month-by-month projection of available monthly surplus over at least 12 months for one-time expenses and at least 24 months for recurring expenses, comparing the baseline (no change) vs. the simulated scenario
- **FR-010c**: The simulation MUST show the impact on each active financial goal: updated projected completion date and delay (in months) caused by the simulated expense
- **FR-010d**: The simulation MUST include AI-generated narrative explaining the implications and suggesting at least 2 concrete adjustments (specific goal pauses or category spending reductions) that would offset the impact
- **FR-010e**: Completed simulations MUST be saveable under a user-defined name and accessible for later review and comparison
- **FR-011**: All AI-generated content within simulations MUST reference specific PLN amounts from the user's actual transaction data (not generic percentage tips)
- **FR-011b**: System MUST generate passive background AI recommendations once at least 3 months of transaction history is available, refreshing daily or when significant new data is added; the user can manually trigger a refresh; recommendations display a "last updated" timestamp
- **FR-012**: System MUST allow users to create financial goals with: name, target amount, optional target date, and priority rank
- **FR-012b**: System MUST calculate and display the available monthly surplus (income − total expenses) as the basis for goal allocation
- **FR-013**: System MUST allow the user to define a monthly allocation amount per goal (in PLN or % of surplus); progress accumulates automatically each month based on these allocations
- **FR-013b**: System MUST calculate and display the required monthly savings amount for each active goal based on target amount, deadline, and current accumulated progress
- **FR-014**: System MUST show an emergency expense advisor: given a target amount to free up, list discretionary spending categories with their reducible amounts
- **FR-015**: System MUST show the impact of an emergency expense on each active financial goal with a recovery timeline
- **FR-016**: System MUST allow the user to set a current "financial focus" (e.g., mortgage overpayment, house construction fund, emergency fund) that persists across sessions

### Key Entities

- **Analysis Period**: A time range (typically one month) over which spending is aggregated; supports comparison to adjacent periods
- **Spending Category Summary**: Aggregated spending for a single category within an analysis period, including trend vs. prior period and classification (essential vs. discretionary)
- **Recurring Expense**: A spending pattern repeating at regular intervals, characterized by frequency, average amount, and projected next occurrence date
- **Financial Goal**: A user-defined savings target with a name, target amount, optional deadline, priority rank, monthly allocation amount, and accumulated progress (sum of monthly allocations to date)
- **Financial Focus**: The user's currently active highest-priority financial objective; a single designation that colors affordability and AI guidance
- **Affordability Assessment**: A point-in-time evaluation of a proposed purchase against current financial position, upcoming obligations, and active goals
- **Budget Simulation**: A user-initiated what-if projection with a name, hypothetical expense definition (amount, type, timing), resulting multi-month surplus projection (baseline vs. simulated), per-goal impact analysis, and AI-generated adjustment suggestions
- **AI Recommendation**: A passive, background-generated personalized observation or suggestion derived from the user's transaction history, including specific PLN amounts; distinct from simulation-generated advice which is triggered by a specific what-if input

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: User can determine their total monthly spending in any category within 30 seconds of opening the analysis view, without manual calculation
- **SC-002**: User can identify at least 3 discretionary spending areas they could reduce, using data surfaced by the tool without external prompting
- **SC-003**: User can answer "how much can I overpay on my mortgage this month?" using only data and recommendations available in the tool, without manual calculation
- **SC-004**: User can run a simulation of a significant expense and see its projected impact on all active goals and monthly surplus within 60 seconds of entering the expense details
- **SC-004b**: Simulation results include at least 2 concrete, AI-generated adjustment suggestions (specific goal pauses or category reductions with PLN amounts) to offset the simulated expense's impact
- **SC-004c**: User receives at least 3 passive AI-generated background recommendations after 3 months of data, each citing specific PLN amounts from their actual spending history
- **SC-005**: User can evaluate the financial impact of an unplanned purchase (including goal impact and upcoming obligations) within 60 seconds using the affordability check
- **SC-006**: User can create a financial goal and immediately see a concrete, realistic monthly savings requirement based on their current spending patterns
- **SC-007**: After 12 months of data, the system surfaces all recurring annual expenses (cyclical expenses) before they occur, giving at least 30 days of advance notice
- **SC-008**: When an unexpected expense arises, user can identify specific spending cuts to absorb it within 2 minutes using the emergency advisor

## Clarifications

### Session 2026-03-13

- Q: Who classifies expenses as essential/fixed vs. discretionary/variable? → A: Hybrid — system auto-classifies based on existing spending categories (e.g., mortgage = essential, restaurants = discretionary), and the user can override the classification per category. Per-transaction overrides are out of scope.
- Q: How does progress toward a financial goal accumulate? → A: Monthly surplus allocation — the system calculates available monthly surplus (income − expenses) and the user defines how much of that surplus is directed to each goal; progress accumulates automatically each month without requiring individual transaction linking.
- Q: Where does income data come from for surplus and affordability calculations? → A: Income is already a tagged/categorized transaction type in the existing system; the analysis feature reads it directly to compute monthly surplus without requiring any new income entry flow.
- Q: When are AI insights generated and how fresh must they be? → A: Background generation — insights are automatically regenerated daily or when a significant amount of new transaction data is added; the user can also manually trigger a refresh. The insights view displays a "last updated" timestamp and a refresh button.
- Q: Is exporting reports or data (PDF, CSV) in scope for this feature? → A: Out of scope — this feature is display-only. Export may be addressed in a future feature.
- Spec update: "AI-Powered Financial Insights" (Story 4) renamed and reframed as "Budget Simulation" — an interactive what-if projection tool. User enters a hypothetical significant expense; system projects multi-month surplus impact and per-goal timeline shifts, with AI-generated adjustment suggestions. Passive background AI recommendations are retained as a secondary capability (FR-011b).

## Assumptions

- The system already collects accurately categorized transaction data (receipts, cash transactions, bank transactions) — this feature builds analytical and advisory layers on top of existing data
- Income is already tracked as a tagged/categorized transaction type in the existing system; monthly surplus (income − expenses) is derived directly from this data without any new income entry flow
- The user is the sole or primary household financial decision-maker; multi-user collaborative budget management is out of scope for this feature
- Report and data export (PDF, CSV) is explicitly out of scope for this feature; the analysis experience is display-only within the app
- A single "financial focus" is active at a time; users manage complexity through multiple goals rather than multiple simultaneous focuses
- Standard web application performance expectations apply: analysis views load within 3 seconds, charts render without perceptible lag
- All transaction history is retained indefinitely to support multi-year trend analysis
- AI insight generation runs automatically in the background (daily or on significant data change); users can also manually trigger a refresh; insights display a "last updated" timestamp
