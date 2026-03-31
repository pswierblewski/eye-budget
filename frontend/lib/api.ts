import {
  ReceiptScanListItem,
  ReceiptScanListItemSchema,
  ReceiptScanDetail,
  ReceiptScanDetailSchema,
  ReceiptTransactionItem,
  ReceiptTransactionItemSchema,
  TextRegionsResult,
  TextRegionsResultSchema,
  CategoryItem,
  CategoryItemSchema,
  CreateCategoryRequest,
  VendorItem,
  VendorItemSchema,
  NormalizedProductItem,
  NormalizedProductItemSchema,
  EvaluationRunListItem,
  EvaluationRunListItemSchema,
  EvaluationRunDetail,
  EvaluationRunDetailSchema,
  GroundTruthEntry,
  GroundTruthEntrySchema,
  ConfirmReceiptRequest,
  TransactionModel,
  TaskResponse,
  TaskResponseSchema,
  TaskStatus,
  TaskStatusSchema,
  BankTransactionListItem,
  BankTransactionListItemSchema,
  BankTransactionDetail,
  BankTransactionDetailSchema,
  BankImportResult,
  BankImportResultSchema,
  RecategorizeBankTransactionsResult,
  RecategorizeBankTransactionsResultSchema,
  ReceiptCandidateItem,
  ReceiptCandidateItemSchema,
  BankTxCandidateItem,
  BankTxCandidateItemSchema,
  CashTransactionListItem,
  CashTransactionListItemSchema,
  CashTransactionDetail,
  CashTransactionDetailSchema,
  CashTransactionCreate,
  CashTransactionUpdate,
  CashTxCandidateItem,
  CashTxCandidateItemSchema,
  PaginatedResponse,
  paginatedSchema,
  UnifiedTransaction,
  UnifiedTransactionSchema,
  AnalyticsSummary,
  AnalyticsSummarySchema,
  PromptAnalyticsSummary,
  PromptAnalyticsSummarySchema,
  CategoryClassificationItem,
  CategoryClassificationItemSchema,
  BudgetMonthlyResponse,
  BudgetMonthlyResponseSchema,
  RecurringExpenseItem,
  RecurringExpenseItemSchema,
  CyclicalAlertItem,
  CyclicalAlertItemSchema,
  AffordabilityCheckResponse,
  AffordabilityCheckResponseSchema,
  FinancialFocusResponse,
  FinancialFocusResponseSchema,
  FinancialGoalListItem,
  FinancialGoalListItemSchema,
  MonthlySurplusResponse,
  MonthlySurplusResponseSchema,
  BudgetSimulationListItem,
  BudgetSimulationListItemSchema,
  BudgetSimulationDetail,
  BudgetSimulationDetailSchema,
  AIRecommendationsResponse,
  AIRecommendationsResponseSchema,
  EmergencyAdvisorResponse,
  EmergencyAdvisorResponseSchema,
  SimulationTaskResponse,
  SimulationTaskResponseSchema,
  VersionInfo,
  VersionInfoSchema,
} from "./types";
import { z } from "zod";

async function apiFetch<T>(
  url: string,
  schema: z.ZodType<T>,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  const json = await res.json();
  return schema.parse(json);
}

export async function listReceipts(
  params: {
    page?: number; limit?: number; status?: string; sort_by?: string; sort_dir?: string;
    search?: string; vendor?: string; product?: string;
    date_from?: string; date_to?: string;
    total_min?: number; total_max?: number;
    tag?: string;
  } = {}
): Promise<PaginatedResponse<ReceiptScanListItem>> {
  const { page = 1, limit = 50, status, sort_by = "id", sort_dir = "desc", search, vendor, product, date_from, date_to, total_min, total_max, tag } = params;
  const offset = (page - 1) * limit;
  const qs = new URLSearchParams({ limit: String(limit), offset: String(offset), sort_by, sort_dir });
  if (status) qs.set("status", status);
  if (search) qs.set("search", search);
  if (vendor) qs.set("vendor", vendor);
  if (product) qs.set("product", product);
  if (date_from) qs.set("date_from", date_from);
  if (date_to) qs.set("date_to", date_to);
  if (total_min != null) qs.set("total_min", String(total_min));
  if (total_max != null) qs.set("total_max", String(total_max));
  if (tag) qs.set("tag", tag);
  return apiFetch(
    `/api/receipts?${qs}`,
    paginatedSchema(ReceiptScanListItemSchema)
  );
}

export async function getReceiptCounts(): Promise<Record<string, number>> {
  return apiFetch("/api/receipts/counts", z.record(z.number()));
}

export async function getReceipt(id: number): Promise<ReceiptScanDetail> {
  return apiFetch(`/api/receipts/${id}`, ReceiptScanDetailSchema);
}

export async function confirmReceipt(
  id: number,
  body: ConfirmReceiptRequest
): Promise<ReceiptScanDetail> {
  return apiFetch(`/api/receipts/${id}/confirm`, ReceiptScanDetailSchema, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function reopenReceipt(id: number): Promise<ReceiptScanDetail> {
  return apiFetch(`/api/receipts/${id}/reopen`, ReceiptScanDetailSchema, {
    method: "POST",
  });
}

export async function updateTransactionItem(
  itemId: number,
  data: Partial<{
    category_id: number;
    product_id: number;
    quantity: number;
    unit_price: number;
    price: number;
  }>
): Promise<ReceiptTransactionItem> {
  return apiFetch(
    `/api/receipts/items/${itemId}`,
    ReceiptTransactionItemSchema,
    {
      method: "PATCH",
      body: JSON.stringify(data),
    }
  );
}

export async function deleteTransactionItem(itemId: number): Promise<void> {
  const res = await fetch(`/api/receipts/items/${itemId}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}

export async function deleteReceipt(id: number): Promise<void> {
  const res = await fetch(`/api/receipts/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}

export async function retryReceipt(id: number): Promise<TaskResponse> {
  return apiFetch(`/api/receipts/${id}/retry`, TaskResponseSchema, {
    method: "POST",
  });
}

export async function reuployReceiptImage(id: number): Promise<void> {
  const res = await fetch(`/api/receipts/${id}/reupload-image`, { method: "POST" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}

export async function localizeReceipt(id: number): Promise<TextRegionsResult> {
  return apiFetch(`/api/receipts/${id}/localize`, TextRegionsResultSchema, {
    method: "POST",
  });
}

export async function listCategories(): Promise<CategoryItem[]> {
  return apiFetch("/api/categories", z.array(CategoryItemSchema));
}

export async function createCategory(
  name: string,
  parent_id: number | null
): Promise<CategoryItem> {
  const body: CreateCategoryRequest = { name, parent_id };
  return apiFetch("/api/categories", CategoryItemSchema, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function listVendors(): Promise<VendorItem[]> {
  return apiFetch("/api/vendors", z.array(VendorItemSchema));
}

export async function createVendor(name: string): Promise<VendorItem> {
  return apiFetch("/api/vendors", VendorItemSchema, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function listProducts(): Promise<NormalizedProductItem[]> {
  return apiFetch("/api/products", z.array(NormalizedProductItemSchema));
}

export async function createProduct(name: string): Promise<NormalizedProductItem> {
  return apiFetch("/api/products", NormalizedProductItemSchema, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function listEvaluations(
  params: { page?: number; limit?: number; sort_by?: string; sort_dir?: string } = {}
): Promise<PaginatedResponse<EvaluationRunListItem>> {
  const { page = 1, limit = 50, sort_by = "id", sort_dir = "desc" } = params;
  const offset = (page - 1) * limit;
  const qs = new URLSearchParams({ limit: String(limit), offset: String(offset), sort_by, sort_dir });
  return apiFetch(
    `/api/evaluations?${qs}`,
    paginatedSchema(EvaluationRunListItemSchema)
  );
}

export async function getEvaluation(id: number): Promise<EvaluationRunDetail> {
  return apiFetch(`/api/evaluations/${id}`, EvaluationRunDetailSchema);
}

export async function listGroundTruth(
  params: { page?: number; limit?: number; sort_by?: string; sort_dir?: string } = {}
): Promise<PaginatedResponse<GroundTruthEntry>> {
  const { page = 1, limit = 50, sort_by = "created_at", sort_dir = "desc" } = params;
  const offset = (page - 1) * limit;
  const qs = new URLSearchParams({ limit: String(limit), offset: String(offset), sort_by, sort_dir });
  return apiFetch(
    `/api/ground-truth?${qs}`,
    paginatedSchema(GroundTruthEntrySchema)
  );
}

export async function getGroundTruth(id: number): Promise<GroundTruthEntry> {
  return apiFetch(`/api/ground-truth/${id}`, GroundTruthEntrySchema);
}

export async function updateGroundTruth(
  id: number,
  body: TransactionModel
): Promise<GroundTruthEntry> {
  return apiFetch(`/api/ground-truth/${id}`, GroundTruthEntrySchema, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function processReceipts(): Promise<TaskResponse> {
  return apiFetch("/api/receipts/process", TaskResponseSchema, { method: "POST" });
}

export async function runEvaluation(entryIds?: number[]): Promise<TaskResponse> {
  return apiFetch("/api/evaluations/run", TaskResponseSchema, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ entry_ids: entryIds ?? null }),
  });
}

export async function getTaskStatus(taskId: string): Promise<TaskStatus> {
  return apiFetch(`/api/tasks/${taskId}`, TaskStatusSchema);
}

// ------------------------------------------------------------------
// Bank transactions
// ------------------------------------------------------------------

export async function importBankCsv(file: File): Promise<BankImportResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch("/api/bank-transactions/import", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  const json = await res.json();
  return BankImportResultSchema.parse(json);
}

export async function recategorizeBankTransactions(): Promise<RecategorizeBankTransactionsResult> {
  return apiFetch(
    "/api/bank-transactions/recategorize",
    RecategorizeBankTransactionsResultSchema,
    { method: "POST" }
  );
}

export async function listBankTransactions(
  params: { page?: number; limit?: number; sort_by?: string; sort_dir?: string; tag?: string } = {}
): Promise<PaginatedResponse<BankTransactionListItem>> {
  const { page = 1, limit = 50, sort_by = "booking_date", sort_dir = "desc", tag } = params;
  const offset = (page - 1) * limit;
  const qs = new URLSearchParams({ limit: String(limit), offset: String(offset), sort_by, sort_dir });
  if (tag) qs.set("tag", tag);
  return apiFetch(`/api/bank-transactions?${qs}`, paginatedSchema(BankTransactionListItemSchema));
}

export async function getBankTransaction(
  id: number
): Promise<BankTransactionDetail> {
  return apiFetch(`/api/bank-transactions/${id}`, BankTransactionDetailSchema);
}

export async function saveBankTransactionCategory(
  id: number,
  categoryId: number | null
): Promise<BankTransactionDetail> {
  return apiFetch(
    `/api/bank-transactions/${id}/category`,
    BankTransactionDetailSchema,
    { method: "PATCH", body: JSON.stringify({ category_id: categoryId }) }
  );
}

// ------------------------------------------------------------------
// Bank ↔ Receipt linking
// ------------------------------------------------------------------

export async function getReceiptCandidates(
  bankTxId: number
): Promise<ReceiptCandidateItem[]> {
  return apiFetch(
    `/api/bank-transactions/${bankTxId}/receipt-candidates`,
    z.array(ReceiptCandidateItemSchema)
  );
}

export async function getBankTxCandidates(
  scanId: number
): Promise<BankTxCandidateItem[]> {
  return apiFetch(
    `/api/receipts/${scanId}/bank-transaction-candidates`,
    z.array(BankTxCandidateItemSchema)
  );
}

export async function linkBankToReceipt(
  bankTxId: number,
  receiptTransactionId: number
): Promise<BankTransactionDetail> {
  return apiFetch(
    `/api/bank-transactions/${bankTxId}/link`,
    BankTransactionDetailSchema,
    {
      method: "POST",
      body: JSON.stringify({ receipt_transaction_id: receiptTransactionId }),
    }
  );
}

export async function unlinkBankTransaction(
  bankTxId: number
): Promise<BankTransactionDetail> {
  const res = await fetch(`/api/bank-transactions/${bankTxId}/link`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  const json = await res.json();
  return BankTransactionDetailSchema.parse(json);
}

// ------------------------------------------------------------------
// Tags
// ------------------------------------------------------------------

export async function getAllTags(): Promise<string[]> {
  return apiFetch("/api/tags", z.array(z.string()));
}

export async function updateReceiptTags(
  id: number,
  tags: string[]
): Promise<ReceiptScanDetail> {
  return apiFetch(`/api/receipts/${id}/tags`, ReceiptScanDetailSchema, {
    method: "PATCH",
    body: JSON.stringify({ tags }),
  });
}

export async function updateBankTransactionTags(
  id: number,
  tags: string[]
): Promise<BankTransactionDetail> {
  return apiFetch(`/api/bank-transactions/${id}/tags`, BankTransactionDetailSchema, {
    method: "PATCH",
    body: JSON.stringify({ tags }),
  });
}

export async function deleteBankTransaction(id: number): Promise<void> {
  const res = await fetch(`/api/bank-transactions/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}

// ------------------------------------------------------------------
// Cash transactions
// ------------------------------------------------------------------

export async function listCashTransactions(
  params: { page?: number; limit?: number; sort_by?: string; sort_dir?: string; tag?: string } = {}
): Promise<PaginatedResponse<CashTransactionListItem>> {
  const { page = 1, limit = 50, sort_by = "booking_date", sort_dir = "desc", tag } = params;
  const offset = (page - 1) * limit;
  const qs = new URLSearchParams({ limit: String(limit), offset: String(offset), sort_by, sort_dir });
  if (tag) qs.set("tag", tag);
  return apiFetch(`/api/cash-transactions?${qs}`, paginatedSchema(CashTransactionListItemSchema));
}

export async function createCashTransaction(
  data: CashTransactionCreate
): Promise<CashTransactionDetail> {
  return apiFetch("/api/cash-transactions", CashTransactionDetailSchema, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function createCashFromReceipt(
  scanId: number
): Promise<CashTransactionDetail> {
  return apiFetch(
    `/api/cash-transactions/from-receipt/${scanId}`,
    CashTransactionDetailSchema,
    { method: "POST" }
  );
}

export async function getCashTransaction(id: number): Promise<CashTransactionDetail> {
  return apiFetch(`/api/cash-transactions/${id}`, CashTransactionDetailSchema);
}

export async function updateCashTransaction(
  id: number,
  data: CashTransactionUpdate
): Promise<CashTransactionDetail> {
  return apiFetch(`/api/cash-transactions/${id}`, CashTransactionDetailSchema, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteCashTransaction(id: number): Promise<void> {
  const res = await fetch(`/api/cash-transactions/${id}`, { method: "DELETE" });
  if (!res.ok && res.status !== 204) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}

export async function saveCashTransactionCategory(
  id: number,
  categoryId: number | null
): Promise<CashTransactionDetail> {
  return apiFetch(
    `/api/cash-transactions/${id}/category`,
    CashTransactionDetailSchema,
    { method: "PATCH", body: JSON.stringify({ category_id: categoryId }) }
  );
}

export async function getCashReceiptCandidates(
  cashTxId: number
): Promise<ReceiptCandidateItem[]> {
  return apiFetch(
    `/api/cash-transactions/${cashTxId}/receipt-candidates`,
    z.array(ReceiptCandidateItemSchema)
  );
}

export async function linkCashToReceipt(
  cashTxId: number,
  receiptTransactionId: number
): Promise<CashTransactionDetail> {
  return apiFetch(
    `/api/cash-transactions/${cashTxId}/link`,
    CashTransactionDetailSchema,
    {
      method: "POST",
      body: JSON.stringify({ receipt_transaction_id: receiptTransactionId }),
    }
  );
}

export async function unlinkCashTransaction(
  cashTxId: number
): Promise<CashTransactionDetail> {
  const res = await fetch(`/api/cash-transactions/${cashTxId}/link`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  const json = await res.json();
  return CashTransactionDetailSchema.parse(json);
}

export async function updateCashTransactionTags(
  id: number,
  tags: string[]
): Promise<CashTransactionDetail> {
  return apiFetch(`/api/cash-transactions/${id}/tags`, CashTransactionDetailSchema, {
    method: "PATCH",
    body: JSON.stringify({ tags }),
  });
}

export async function getCashTxCandidatesForReceipt(
  scanId: number
): Promise<CashTxCandidateItem[]> {
  return apiFetch(
    `/api/receipts/${scanId}/cash-transaction-candidates`,
    z.array(CashTxCandidateItemSchema)
  );
}

// ------------------------------------------------------------------
// Unified transactions
// ------------------------------------------------------------------

export async function listUnifiedTransactions(
  params: {
    page?: number;
    limit?: number;
    status?: string;
    source_type?: string;
    date_from?: string;
    date_to?: string;
    category_id?: number;
    tag?: string;
    search?: string;
    amount_min?: number;
    amount_max?: number;
    direction?: string;
    sort_by?: string;
    sort_dir?: string;
  } = {}
): Promise<PaginatedResponse<UnifiedTransaction>> {
  const {
    page = 1,
    limit = 50,
    status,
    source_type,
    date_from,
    date_to,
    category_id,
    tag,
    search,
    amount_min,
    amount_max,
    direction,
    sort_by = "date",
    sort_dir = "desc",
  } = params;
  const offset = (page - 1) * limit;
  const qs = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    sort_by,
    sort_dir,
  });
  if (status) qs.set("status", status);
  if (source_type) qs.set("source_type", source_type);
  if (date_from) qs.set("date_from", date_from);
  if (date_to) qs.set("date_to", date_to);
  if (category_id != null) qs.set("category_id", String(category_id));
  if (tag) qs.set("tag", tag);
  if (search) qs.set("search", search);
  if (amount_min != null) qs.set("amount_min", String(amount_min));
  if (amount_max != null) qs.set("amount_max", String(amount_max));
  if (direction) qs.set("direction", direction);
  return apiFetch(
    `/api/transactions?${qs}`,
    paginatedSchema(UnifiedTransactionSchema)
  );
}

export async function getTransactionsAnalytics(
  params: { date_from?: string; date_to?: string } = {}
): Promise<AnalyticsSummary> {
  const qs = new URLSearchParams();
  if (params.date_from) qs.set("date_from", params.date_from);
  if (params.date_to) qs.set("date_to", params.date_to);
  const query = qs.toString();
  return apiFetch(
    `/api/transactions/analytics${query ? `?${query}` : ""}`,
    AnalyticsSummarySchema
  );
}

export async function getPromptAnalytics(): Promise<PromptAnalyticsSummary> {
  return apiFetch("/api/prompt-analytics", PromptAnalyticsSummarySchema);
}

// ---------------------------------------------------------------------------
// Budget Analysis API functions
// ---------------------------------------------------------------------------

export async function getBudgetMonthly(
  year: number,
  month: number
): Promise<BudgetMonthlyResponse> {
  return apiFetch(
    `/api/budget/analysis/monthly?year=${year}&month=${month}`,
    BudgetMonthlyResponseSchema
  );
}

export async function getBudgetCategoryClassifications(): Promise<CategoryClassificationItem[]> {
  return apiFetch(
    "/api/budget/category-classifications",
    CategoryClassificationItemSchema.array()
  );
}

export async function updateBudgetCategoryClassification(
  categoryId: number,
  classification: string
): Promise<CategoryClassificationItem> {
  return apiFetch(
    `/api/budget/category-classifications/${categoryId}`,
    CategoryClassificationItemSchema,
    { method: "PUT", body: JSON.stringify({ classification }) }
  );
}

export async function getFinancialFocus(): Promise<FinancialFocusResponse> {
  return apiFetch("/api/budget/financial-focus", FinancialFocusResponseSchema);
}

export async function setFinancialFocus(
  label: string,
  description?: string
): Promise<FinancialFocusResponse> {
  return apiFetch(
    "/api/budget/financial-focus",
    FinancialFocusResponseSchema,
    { method: "PUT", body: JSON.stringify({ label, description }) }
  );
}

export async function getBudgetRecurringExpenses(): Promise<RecurringExpenseItem[]> {
  return apiFetch(
    "/api/budget/analysis/recurring-expenses",
    RecurringExpenseItemSchema.array()
  );
}

export async function getBudgetCyclicalAlerts(): Promise<CyclicalAlertItem[]> {
  return apiFetch(
    "/api/budget/analysis/cyclical-alerts",
    CyclicalAlertItemSchema.array()
  );
}

export async function checkAffordability(
  amount_pln: number
): Promise<AffordabilityCheckResponse> {
  return apiFetch(
    `/api/budget/analysis/affordability?amount_pln=${amount_pln}`,
    AffordabilityCheckResponseSchema
  );
}

export async function getBudgetGoals(): Promise<FinancialGoalListItem[]> {
  return apiFetch("/api/budget/goals", FinancialGoalListItemSchema.array());
}

export async function getBudgetSurplus(): Promise<MonthlySurplusResponse> {
  return apiFetch("/api/budget/goals/surplus", MonthlySurplusResponseSchema);
}

export async function createGoal(data: {
  name: string;
  target_amount_pln: number;
  target_date?: string;
  priority_rank?: number;
  monthly_allocation_amount_pln?: number;
}): Promise<FinancialGoalListItem> {
  return apiFetch("/api/budget/goals", FinancialGoalListItemSchema, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateGoal(
  id: number,
  data: Partial<{
    name: string;
    target_amount_pln: number;
    target_date: string;
    priority_rank: number;
    monthly_allocation_amount_pln: number;
    is_active: boolean;
  }>
): Promise<FinancialGoalListItem> {
  return apiFetch(`/api/budget/goals/${id}`, FinancialGoalListItemSchema, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteGoal(id: number): Promise<void> {
  const res = await fetch(`/api/budget/goals/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}

export async function getBudgetSimulations(): Promise<BudgetSimulationListItem[]> {
  return apiFetch(
    "/api/budget/simulations",
    BudgetSimulationListItemSchema.array()
  );
}

export async function getBudgetSimulation(id: number): Promise<BudgetSimulationDetail> {
  return apiFetch(`/api/budget/simulations/${id}`, BudgetSimulationDetailSchema);
}

export async function createBudgetSimulation(data: {
  name: string;
  expense_name: string;
  expense_amount_pln: number;
  expense_type: string;
  expense_start_date: string;
}): Promise<SimulationTaskResponse> {
  return apiFetch("/api/budget/simulations", SimulationTaskResponseSchema, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deleteBudgetSimulation(id: number): Promise<void> {
  const res = await fetch(`/api/budget/simulations/${id}`, { method: "DELETE" });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}

export async function getAIRecommendations(): Promise<AIRecommendationsResponse> {
  return apiFetch(
    "/api/budget/ai-recommendations",
    AIRecommendationsResponseSchema
  );
}

export async function refreshAIRecommendations(): Promise<TaskResponse> {
  return apiFetch(
    "/api/budget/ai-recommendations/refresh",
    TaskResponseSchema,
    { method: "POST" }
  );
}

export async function getEmergencyAdvice(
  amount_pln: number,
  description?: string
): Promise<EmergencyAdvisorResponse> {
  return apiFetch(
    "/api/budget/emergency-advisor",
    EmergencyAdvisorResponseSchema,
    {
      method: "POST",
      body: JSON.stringify({ amount_pln, description }),
    }
  );
}

export async function getVersionInfo(): Promise<VersionInfo> {
  return apiFetch("/api/version", VersionInfoSchema);
}
