# API Contracts: Budget Simulation & AI Recommendations

**Branch**: `001-budget-analysis` | **Date**: 2026-03-13  
All routes in `backend/src/main.py` under `# --- Budget Analysis ---`.

---

## Budget Simulation

### POST /budget/simulations

Creates a new simulation and enqueues the Celery task for computation.

**Body**: `CreateBudgetSimulationRequest`
```json
{
  "name": "Okna w domu – co się stanie?",
  "expense_name": "Wymiana okien",
  "expense_amount_pln": 20000.00,
  "expense_type": "one_time",
  "expense_start_date": "2026-06-01"
}
```

**Response 202**: `TaskResponse`
```json
{
  "task_id": "celery-task-uuid",
  "simulation_id": 7
}
```

**Notes**:
- HTTP 202 always — never blocks waiting for computation.
- The Celery task `run_budget_simulation` picks it up, runs the projection + OpenAI call, stores the result in `budget_simulations.result_json`, then pushes to Pusher channel `budget-channel` event `budget.simulation.done` with `{ "simulation_id": 7, "status": "done" }`.
- On failure: event `budget.simulation.failed` with `{ "simulation_id": 7, "error": "..." }`.
- Frontend subscribes to `budget-channel` while on the simulations page and calls `queryClient.invalidateQueries(["budget-simulations", id])` on `budget.simulation.done`.

**Errors**: `400` if `expense_amount_pln` ≤ 0 or `expense_type` not in `['one_time', 'recurring']`.

---

### GET /budget/simulations

Returns all simulations ordered by `created_at` descending.

**Response 200**: `list[BudgetSimulationListItem]`
```json
[
  {
    "id": 7,
    "name": "Okna w domu – co się stanie?",
    "expense_name": "Wymiana okien",
    "expense_amount_pln": 20000.00,
    "expense_type": "one_time",
    "expense_start_date": "2026-06-01",
    "status": "done",
    "created_at": "2026-03-13T10:30:00"
  }
]
```

---

### GET /budget/simulations/{id}

Returns full simulation detail including results.

**Path param**: `id` (int)  
**Response 200**: `BudgetSimulationDetail`
```json
{
  "id": 7,
  "name": "Okna w domu – co się stanie?",
  "expense_name": "Wymiana okien",
  "expense_amount_pln": 20000.00,
  "expense_type": "one_time",
  "expense_start_date": "2026-06-01",
  "status": "done",
  "result": {
    "projection": [
      { "month": "2026-04", "baseline_surplus_pln": 6800.00, "simulated_surplus_pln": 6800.00 },
      { "month": "2026-05", "baseline_surplus_pln": 6800.00, "simulated_surplus_pln": 6800.00 },
      { "month": "2026-06", "baseline_surplus_pln": 6800.00, "simulated_surplus_pln": -13200.00 },
      { "month": "2026-07", "baseline_surplus_pln": 6800.00, "simulated_surplus_pln": 6800.00 }
    ],
    "goal_impacts": [
      {
        "goal_id": 1,
        "goal_name": "Nadpłata kredytu hipotecznego",
        "baseline_completion_date": "2030-02-01",
        "simulated_completion_date": "2030-05-01",
        "delay_months": 3
      }
    ],
    "ai_summary": "Wymiana okien za 20 000 zł w czerwcu 2026 spowoduje jednorazowy duży odpływ gotówki. Czerwiec skończy się na minusie, co oznacza konieczność finansowania z oszczędności lub wcześniej zebranego bufora.",
    "ai_implications": "Cel 'Nadpłata kredytu hipotecznego' zostanie opóźniony o ok. 3 miesiące. W miesiącu zakupu nie będzie możliwości realizacji żadnej alokacji celów.",
    "ai_suggestions": [
      {
        "description": "Zacznij odkładać 1 700 zł miesięcznie przez 12 miesięcy, aby zgromadzić środki przed zakupem i uniknąć deficytu w czerwcu.",
        "monthly_saving_pln": 1700.00,
        "months_required": 12
      },
      {
        "description": "Ograniczenie wydatków na restauracje i rozrywkę o 400 zł/miesiąc skróci czas zbierania o 2 miesiące.",
        "monthly_saving_pln": 400.00,
        "months_required": 10
      }
    ]
  },
  "error_message": null,
  "created_at": "2026-03-13T10:30:00"
}
```

**Errors**: `404` if simulation not found.  
**Polling strategy**: Frontend polls this endpoint every 3 seconds while status is `pending` or `processing`, or waits for the Pusher event (whichever comes first).

---

### DELETE /budget/simulations/{id}

Deletes a simulation and its results.

**Path param**: `id` (int)  
**Response 204**  
**Errors**: `404` if not found.

---

## AI Recommendations

### GET /budget/ai-recommendations

Returns the current AI-generated background recommendations.

**Response 200**: `AIRecommendationsResponse`
```json
{
  "insights": [
    {
      "title": "Wydatki na restauracje rosną",
      "body": "W ostatnich 3 miesiącach wydałeś średnio 580 zł/miesiąc na restauracje. To o 140 zł więcej niż 6 miesięcy temu. Ograniczenie do 400 zł/miesiąc dałoby 180 zł więcej na nadpłatę kredytu.",
      "amount_pln": 180.00,
      "insight_type": "saving_opportunity"
    },
    {
      "title": "Możliwa nadpłata kredytu: ~1 200 zł/miesiąc",
      "body": "Na podstawie Twoich danych z ostatnich 3 miesięcy, po uwzględnieniu wszystkich alokacji celów, dysponujesz ok. 1 200 zł miesięcznie nadwyżki. To realistyczna kwota nadpłaty kredytu bez obcinania niezbędnych wydatków.",
      "amount_pln": 1200.00,
      "insight_type": "goal_advice"
    }
  ],
  "generated_at": "2026-03-13T06:00:00",
  "data_through_date": "2026-03-12",
  "months_of_data": 5,
  "has_sufficient_data": true
}
```

**Notes**:
- If no recommendations exist yet: returns `insights: []`, `has_sufficient_data: false` (< 3 months data), `generated_at: null`.
- `has_sufficient_data: false` triggers a "Zbieramy dane..." placeholder in the UI.

---

### POST /budget/ai-recommendations/refresh

Manually triggers regeneration of AI recommendations.

**Body**: none  
**Response 202**: `TaskResponse`
```json
{ "task_id": "celery-task-uuid" }
```

**Notes**:
- Celery task `refresh_ai_recommendations` runs the OpenAI call and updates `budget_ai_recommendations` table.
- On completion: Pusher event `budget.recommendations.done` on `budget-channel` with `{ "generated_at": "2026-03-13T12:00:00" }`.
- Frontend invalidates `["budget-ai-recommendations"]` query on this event.
- Returns `409` if a refresh task is already running (check `status = 'processing'` — not applicable here, but recommendations generation is gated by checking if a recent one was generated in the last 15 minutes).
