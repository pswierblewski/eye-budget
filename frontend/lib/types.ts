import { z } from "zod";

// Generic paginated response
export function paginatedSchema<T>(itemSchema: z.ZodType<T>) {
  return z.object({
    items: z.array(itemSchema),
    total: z.number(),
    limit: z.number(),
    offset: z.number(),
  });
}

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export const ReceiptScanListItemSchema = z.object({
  id: z.number(),
  filename: z.string(),
  status: z.string(),
  vendor: z.string().nullable(),
  date: z.string().nullable(),
  total: z.number().nullable(),
  tags: z.array(z.string()).optional(),
});
export type ReceiptScanListItem = z.infer<typeof ReceiptScanListItemSchema>;

export const ReceiptTransactionItemSchema = z.object({
  id: z.number(),
  product_id: z.number().nullable(),
  raw_product_name: z.string(),
  normalized_product_name: z.string().nullable(),
  category_id: z.number(),
  quantity: z.number(),
  unit_price: z.number().nullable(),
  price: z.number(),
});
export type ReceiptTransactionItem = z.infer<typeof ReceiptTransactionItemSchema>;

export const ReceiptTransactionSchema = z.object({
  id: z.number(),
  vendor_id: z.number().nullable(),
  raw_vendor_name: z.string(),
  normalized_vendor_name: z.string().nullable(),
  date: z.string(),
  total: z.number(),
  items: z.array(ReceiptTransactionItemSchema),
});
export type ReceiptTransaction = z.infer<typeof ReceiptTransactionSchema>;

export const ProductItemSchema = z.object({
  name: z.string(),
  quantity: z.number(),
  price: z.number(),
  unit_price: z.number().nullable(),
});
export type ProductItem = z.infer<typeof ProductItemSchema>;

export const CategoryCandidateSchema = z.object({
  category_id: z.number(),
  category_name: z.string(),
  category_score: z.number(),
});

export const BankTransactionSplitSchema = z.object({
  id: z.number(),
  category_id: z.number(),
  category_name: z.string(),
  amount: z.number(),
});
export type BankTransactionSplit = z.infer<typeof BankTransactionSplitSchema>;

export const CategoryCandidatesSchema = z.object({
  product_name: z.string(),
  category_candidates: z.array(CategoryCandidateSchema),
});

export const TransactionModelSchema = z.object({
  vendor: z.string(),
  title: z.string(),
  products: z.array(ProductItemSchema),
  total: z.number(),
  date: z.string(),
});
export type TransactionModel = z.infer<typeof TransactionModelSchema>;

// ------------------------------------------------------------------
// Bank ↔ Receipt linking (declared early — used by ReceiptScanDetail and BankTransactionDetail)
// ------------------------------------------------------------------

export const ReceiptLinkInfoSchema = z.object({
  receipt_transaction_id: z.number(),
  scan_id: z.number(),
  scan_filename: z.string(),
  vendor_name: z.string(),
  date: z.string(),
  total: z.number(),
});
export type ReceiptLinkInfo = z.infer<typeof ReceiptLinkInfoSchema>;

export const BankLinkInfoSchema = z.object({
  bank_transaction_id: z.number(),
  counterparty: z.string().nullable(),
  booking_date: z.string(),
  amount: z.number(),
});
export type BankLinkInfo = z.infer<typeof BankLinkInfoSchema>;

export const ReceiptCandidateItemSchema = z.object({
  receipt_transaction_id: z.number(),
  scan_id: z.number(),
  scan_filename: z.string(),
  vendor_name: z.string(),
  date: z.string(),
  total: z.number(),
  match_score: z.number(),
});
export type ReceiptCandidateItem = z.infer<typeof ReceiptCandidateItemSchema>;

export const BankTxCandidateItemSchema = z.object({
  bank_transaction_id: z.number(),
  counterparty: z.string().nullable(),
  booking_date: z.string(),
  amount: z.number(),
  match_score: z.number(),
});
export type BankTxCandidateItem = z.infer<typeof BankTxCandidateItemSchema>;

export const CashLinkInfoSchema = z.object({
  cash_transaction_id: z.number(),
  description: z.string().nullable(),
  booking_date: z.string(),
  amount: z.number(),
});
export type CashLinkInfo = z.infer<typeof CashLinkInfoSchema>;

export const CashTxCandidateItemSchema = z.object({
  cash_transaction_id: z.number(),
  description: z.string().nullable(),
  booking_date: z.string(),
  amount: z.number(),
  match_score: z.number(),
});
export type CashTxCandidateItem = z.infer<typeof CashTxCandidateItemSchema>;

export const ProductTextRegionSchema = z.object({
  polygon: z.array(z.array(z.number())),
});
export type ProductTextRegion = z.infer<typeof ProductTextRegionSchema>;

export const TextRegionsResultSchema = z.object({
  image_width: z.number(),
  image_height: z.number(),
  product_regions: z.record(ProductTextRegionSchema),
});
export type TextRegionsResult = z.infer<typeof TextRegionsResultSchema>;

export const ReceiptScanDetailSchema = z.object({
  id: z.number(),
  filename: z.string(),
  status: z.string(),
  result: TransactionModelSchema.nullable(),
  categories_candidates: z
    .object({
      category_candidates: z.array(CategoryCandidatesSchema),
    })
    .nullable(),
  minio_object_key: z.string().nullable(),
  transaction: ReceiptTransactionSchema.nullable(),
  bank_link: BankLinkInfoSchema.nullable().optional(),
  cash_link: CashLinkInfoSchema.nullable().optional(),
  vendor_normalization: z.string().nullable().optional(),
  product_normalizations: z.record(z.string().nullable()).nullable().optional(),
  tags: z.array(z.string()).optional(),
  bank_candidate_count: z.number().optional(),
  cash_candidate_count: z.number().optional(),
  text_regions: TextRegionsResultSchema.optional().nullable(),
});
export type ReceiptScanDetail = z.infer<typeof ReceiptScanDetailSchema>;

export const CategoryItemSchema = z.object({
  id: z.number(),
  name: z.string(),
  parent_name: z.string().nullable(),
});
export type CategoryItem = z.infer<typeof CategoryItemSchema>;

export const ReceiptCategorySchema = z.object({
  id: z.number(),
  name: z.string(),
  product_count: z.number(),
});
export type ReceiptCategory = z.infer<typeof ReceiptCategorySchema>;

export type CreateCategoryRequest = {
  name: string;
  parent_id: number | null;
};

export const VendorItemSchema = z.object({
  id: z.number(),
  name: z.string(),
});
export type VendorItem = z.infer<typeof VendorItemSchema>;

export const NormalizedProductItemSchema = z.object({
  id: z.number(),
  name: z.string(),
});
export type NormalizedProductItem = z.infer<typeof NormalizedProductItemSchema>;

export const EvaluationRunListItemSchema = z.object({
  id: z.number(),
  run_timestamp: z.string(),
  model_used: z.string(),
  total_files: z.number(),
  successful: z.number(),
  failed: z.number(),
  success_rate: z.number().nullable(),
  avg_processing_time_ms: z.number().nullable(),
  avg_field_completeness: z.number().nullable(),
  avg_consistency_rate: z.number().nullable(),
  config: z.record(z.unknown()).nullable(),
});
export type EvaluationRunListItem = z.infer<typeof EvaluationRunListItemSchema>;

export const EvaluationResultSchema = z.object({
  filename: z.string(),
  success: z.boolean(),
  error_message: z.string().nullable(),
  metrics: z
    .object({
      processing_time_ms: z.number(),
      fields_extracted: z.number(),
      field_completeness: z.number(),
      product_count: z.number(),
      has_vendor: z.boolean(),
      has_date: z.boolean(),
      has_total: z.boolean(),
      products_sum: z.number(),
      extracted_total: z.number(),
      total_difference: z.number(),
      is_consistent: z.boolean(),
      vendor_correct: z.boolean().nullable().optional(),
      date_correct: z.boolean().nullable().optional(),
      total_correct: z.boolean().nullable().optional(),
      total_accuracy: z.number().nullable().optional(),
      product_count_correct: z.boolean().nullable().optional(),
      products_accuracy: z.number().nullable().optional(),
    })
    .nullable(),
  transaction: TransactionModelSchema.nullable(),
});

export const EvaluationRunDetailSchema = EvaluationRunListItemSchema.extend({
  results: z.array(EvaluationResultSchema),
});
export type EvaluationRunDetail = z.infer<typeof EvaluationRunDetailSchema>;

export const GroundTruthEntrySchema = z.object({
  id: z.number(),
  filename: z.string(),
  ground_truth: TransactionModelSchema,
  created_at: z.string(),
});
export type GroundTruthEntry = z.infer<typeof GroundTruthEntrySchema>;

export type ConfirmReceiptRequest = {
  product_categories: Record<string, number>;
  // Optional overrides for OCR-sourced fields
  vendor?: string | null;
  date?: string | null;
  total?: number | null;
  products?: Array<{
    name: string;
    quantity: number;
    price: number;
    unit_price: number | null;
  }> | null;
  // Optional normalized name overrides
  normalized_vendor?: string | null;
  normalized_products?: Record<string, string> | null;
};

// ------------------------------------------------------------------
// Async task response (Celery background jobs)
// ------------------------------------------------------------------

export const TaskResponseSchema = z.object({
  task_id: z.string(),
});
export type TaskResponse = z.infer<typeof TaskResponseSchema>;

export const TaskStatusSchema = z.object({
  task_id: z.string(),
  status: z.string(), // PENDING | STARTED | SUCCESS | FAILURE | RETRY
  result: z.unknown().nullable(),
  error: z.string().nullable(),
});
export type TaskStatus = z.infer<typeof TaskStatusSchema>;

// ------------------------------------------------------------------
// Bank transactions (CSV import)
// ------------------------------------------------------------------

export const BankTransactionListItemSchema = z.object({
  id: z.number(),
  reference_number: z.string(),
  booking_date: z.string(),
  counterparty: z.string().nullable(),
  description: z.string().nullable(),
  amount: z.number(),
  currency: z.string(),
  operation_type: z.string().nullable(),
  category_id: z.number().nullable(),
  category_name: z.string().nullable(),
  tags: z.array(z.string()).optional(),
  receipt_category_name: z.string().nullable().optional(),
  receipt_category_count: z.number().nullable().optional(),
  split_category_name: z.string().nullable().optional(),
  split_count: z.number().nullable().optional(),
});
export type BankTransactionListItem = z.infer<typeof BankTransactionListItemSchema>;

export const BankTransactionDetailSchema = z.object({
  id: z.number(),
  reference_number: z.string(),
  booking_date: z.string(),
  value_date: z.string().nullable(),
  counterparty: z.string().nullable(),
  counterparty_address: z.string().nullable(),
  source_account: z.string().nullable(),
  target_account: z.string().nullable(),
  description: z.string().nullable(),
  amount: z.number(),
  currency: z.string(),
  operation_type: z.string().nullable(),
  category_id: z.number().nullable(),
  category_name: z.string().nullable(),
  category_candidates: z.array(CategoryCandidateSchema).nullable(),
  vendor_id: z.number().nullable(),
  receipt_link: ReceiptLinkInfoSchema.nullable().optional(),
  receipt_categories: z.array(ReceiptCategorySchema).nullable().optional(),
  tags: z.array(z.string()).optional(),
  category_splits: z.array(BankTransactionSplitSchema).nullable().optional(),
});
export type BankTransactionDetail = z.infer<typeof BankTransactionDetailSchema>;

export const BankImportResultSchema = z.object({
  imported: z.number(),
  duplicates: z.number(),
  errors: z.number(),
  task_id: z.string().nullable().optional(),
  auto_linked: z.number().optional().default(0),
  needs_manual_link: z.number().optional(),
});
export type BankImportResult = z.infer<typeof BankImportResultSchema>;

export const RecategorizeBankTransactionsResultSchema = z.object({
  task_id: z.string().nullable().optional(),
  count: z.number(),
});
export type RecategorizeBankTransactionsResult = z.infer<typeof RecategorizeBankTransactionsResultSchema>;

// ------------------------------------------------------------------
// Cash transactions
// ------------------------------------------------------------------

export const CashReceiptLinkInfoSchema = z.object({
  receipt_transaction_id: z.number(),
  scan_id: z.number(),
  scan_filename: z.string(),
  vendor_name: z.string(),
  date: z.string(),
  total: z.number(),
});
export type CashReceiptLinkInfo = z.infer<typeof CashReceiptLinkInfoSchema>;

export const CashTransactionListItemSchema = z.object({
  id: z.number(),
  booking_date: z.string(),
  description: z.string().nullable(),
  amount: z.number(),
  currency: z.string(),
  source: z.string(),
  category_id: z.number().nullable(),
  category_name: z.string().nullable(),
  vendor_id: z.number().nullable(),
  vendor_name: z.string().nullable(),
  tags: z.array(z.string()).optional(),
  receipt_link: CashReceiptLinkInfoSchema.nullable().optional(),
  receipt_category_name: z.string().nullable().optional(),
  receipt_category_count: z.number().nullable().optional(),
  receipt_categories: z.array(ReceiptCategorySchema).nullable().optional(),
});
export type CashTransactionListItem = z.infer<typeof CashTransactionListItemSchema>;

export const CashTransactionDetailSchema = CashTransactionListItemSchema.extend({
  receipt_scan_id: z.number().nullable().optional(),
});
export type CashTransactionDetail = z.infer<typeof CashTransactionDetailSchema>;

export type CashTransactionCreate = {
  booking_date: string;
  amount: number;
  description?: string | null;
  category_id?: number | null;
  vendor_id?: number | null;
};

export type CashTransactionUpdate = {
  booking_date?: string | null;
  amount?: number | null;
  description?: string | null;
  category_id?: number | null;
  vendor_id?: number | null;
};

// ------------------------------------------------------------------
// Unified transactions
// ------------------------------------------------------------------

export const UnifiedTransactionSchema = z.object({
  id: z.number(),
  source_type: z.enum(["bank", "cash", "receipt"]),
  date: z.string(),
  amount: z.number(),
  description: z.string().nullable(),
  vendor_name: z.string().nullable(),
  category_id: z.number().nullable(),
  category_name: z.string().nullable(),
  tags: z.array(z.string()).optional(),
  status: z.string().nullable().optional(),
  has_receipt: z.boolean(),
  receipt_scan_id: z.number().nullable(),
  currency: z.string(),
  receipt_category_name: z.string().nullable().optional(),
  receipt_category_count: z.number().nullable().optional(),
  receipt_categories: z.array(ReceiptCategorySchema).nullable().optional(),
});
export type UnifiedTransaction = z.infer<typeof UnifiedTransactionSchema>;

export const MonthlySummarySchema = z.object({
  month: z.string(),
  expense: z.number(),
  income: z.number(),
});
export type MonthlySummary = z.infer<typeof MonthlySummarySchema>;

export const CategoryBreakdownSchema = z.object({
  name: z.string(),
  total: z.number(),
});
export type CategoryBreakdown = z.infer<typeof CategoryBreakdownSchema>;

export const VendorBreakdownSchema = z.object({
  vendor_name: z.string(),
  total: z.number(),
});
export type VendorBreakdown = z.infer<typeof VendorBreakdownSchema>;

export const MonthOverMonthSchema = z.object({
  current: z.number(),
  previous: z.number(),
  change_pct: z.number(),
});
export type MonthOverMonth = z.infer<typeof MonthOverMonthSchema>;

export const AnalyticsSummarySchema = z.object({
  total_expense: z.number(),
  total_income: z.number(),
  transaction_count: z.number(),
  monthly_totals: z.array(MonthlySummarySchema),
  by_vendor: z.array(VendorBreakdownSchema),
  by_category: z.array(CategoryBreakdownSchema),
  month_over_month: MonthOverMonthSchema,
});
export type AnalyticsSummary = z.infer<typeof AnalyticsSummarySchema>;

// ---------------------------------------------------------------------------
// Prompt analytics
// ---------------------------------------------------------------------------

export const CategoryConfusionItemSchema = z.object({
  ai_category_name: z.string(),
  user_category_name: z.string(),
  count: z.number(),
});
export type CategoryConfusionItem = z.infer<typeof CategoryConfusionItemSchema>;

export const ProductNameCorrectionItemSchema = z.object({
  ai_normalized_name: z.string(),
  user_normalized_name: z.string(),
  count: z.number(),
});
export type ProductNameCorrectionItem = z.infer<typeof ProductNameCorrectionItemSchema>;

export const PromptAnalyticsRowSchema = z.object({
  id: z.number(),
  scan_id: z.number(),
  vendor_name: z.string().nullable(),
  category_corrections_count: z.number(),
  product_name_corrections_count: z.number(),
  ocr_product_count: z.number(),
  confirmed_product_count: z.number(),
  details: z.record(z.unknown()),
  created_at: z.string().nullable(),
});
export type PromptAnalyticsRow = z.infer<typeof PromptAnalyticsRowSchema>;

export const PromptAnalyticsSummarySchema = z.object({
  total_receipts: z.number(),
  total_category_corrections: z.number(),
  total_product_name_corrections: z.number(),
  receipts_with_added_products: z.number(),
  receipts_with_removed_products: z.number(),
  receipts_with_product_count_mismatch: z.number(),
  avg_category_corrections: z.number(),
  avg_product_name_corrections: z.number(),
  avg_ocr_product_count: z.number(),
  top_category_confusions: z.array(CategoryConfusionItemSchema),
  top_product_name_corrections: z.array(ProductNameCorrectionItemSchema),
  recent: z.array(PromptAnalyticsRowSchema),
});
export type PromptAnalyticsSummary = z.infer<typeof PromptAnalyticsSummarySchema>;

// ---------------------------------------------------------------------------
// Budget Analysis schemas
// ---------------------------------------------------------------------------

export const CategoryClassificationItemSchema = z.object({
  category_id: z.number(),
  category_name: z.string(),
  classification: z.enum(["essential", "discretionary"]),
  is_user_override: z.boolean(),
});
export type CategoryClassificationItem = z.infer<typeof CategoryClassificationItemSchema>;

export const BudgetCategoryMonthlyItemSchema = z.object({
  category_id: z.number().nullable(),
  category_name: z.string(),
  classification: z.enum(["essential", "discretionary"]),
  total_pln: z.number(),
  pct_of_total: z.number(),
  prev_month_pln: z.number(),
  change_pct: z.number(),
});
export type BudgetCategoryMonthlyItem = z.infer<typeof BudgetCategoryMonthlyItemSchema>;

export const BudgetMonthlyResponseSchema = z.object({
  year: z.number(),
  month: z.number(),
  total_expenses_pln: z.number(),
  total_income_pln: z.number(),
  surplus_pln: z.number(),
  categories: z.array(BudgetCategoryMonthlyItemSchema),
  prev_month_total_pln: z.number(),
  month_over_month_change_pct: z.number(),
});
export type BudgetMonthlyResponse = z.infer<typeof BudgetMonthlyResponseSchema>;

export const RecurringExpenseItemSchema = z.object({
  vendor_name: z.string(),
  category_name: z.string().nullable(),
  frequency: z.enum(["monthly", "annual"]),
  avg_amount_pln: z.number(),
  last_occurrence_date: z.string(),
  next_expected_date: z.string(),
  amount_min_pln: z.number(),
  amount_max_pln: z.number(),
  occurrence_count: z.number(),
});
export type RecurringExpenseItem = z.infer<typeof RecurringExpenseItemSchema>;

export const CyclicalAlertItemSchema = z.object({
  vendor_name: z.string(),
  category_name: z.string().nullable(),
  next_expected_date: z.string(),
  days_until: z.number(),
  expected_amount_pln: z.number(),
  amount_range_pln: z.string(),
});
export type CyclicalAlertItem = z.infer<typeof CyclicalAlertItemSchema>;

export const AffordabilityCheckResponseSchema = z.object({
  verdict: z.enum(["green", "yellow", "red"]),
  amount_pln: z.number(),
  available_this_month_pln: z.number(),
  upcoming_obligations_30d_pln: z.number(),
  active_goal_allocations_pln: z.number(),
  freely_available_pln: z.number(),
  financial_focus_label: z.string().nullable(),
  narrative: z.string(),
});
export type AffordabilityCheckResponse = z.infer<typeof AffordabilityCheckResponseSchema>;

export const FinancialFocusResponseSchema = z.object({
  id: z.number().nullable(),
  label: z.string(),
  description: z.string().nullable(),
  is_active: z.boolean(),
});
export type FinancialFocusResponse = z.infer<typeof FinancialFocusResponseSchema>;

export const FinancialGoalListItemSchema = z.object({
  id: z.number(),
  name: z.string(),
  target_amount_pln: z.number(),
  target_date: z.string().nullable(),
  priority_rank: z.number(),
  monthly_allocation_amount_pln: z.number(),
  accumulated_progress_pln: z.number(),
  progress_pct: z.number(),
  months_to_completion: z.number().nullable(),
  projected_completion_date: z.string().nullable(),
  is_active: z.boolean(),
});
export type FinancialGoalListItem = z.infer<typeof FinancialGoalListItemSchema>;

export const MonthlySurplusResponseSchema = z.object({
  avg_income_3m_pln: z.number(),
  avg_expenses_3m_pln: z.number(),
  avg_surplus_3m_pln: z.number(),
  current_month_income_pln: z.number(),
  current_month_expenses_pln: z.number(),
  current_month_surplus_pln: z.number(),
  total_monthly_goal_allocations_pln: z.number(),
  unallocated_surplus_pln: z.number(),
});
export type MonthlySurplusResponse = z.infer<typeof MonthlySurplusResponseSchema>;

export const SimulationMonthlyPointSchema = z.object({
  month: z.string(),
  baseline_surplus_pln: z.number(),
  simulated_surplus_pln: z.number(),
});
export type SimulationMonthlyPoint = z.infer<typeof SimulationMonthlyPointSchema>;

export const BudgetSimulationListItemSchema = z.object({
  id: z.number(),
  name: z.string(),
  expense_name: z.string(),
  expense_amount_pln: z.number(),
  expense_type: z.enum(["one_time", "recurring"]),
  expense_start_date: z.string(),
  status: z.enum(["pending", "processing", "done", "failed"]),
  created_at: z.string(),
});
export type BudgetSimulationListItem = z.infer<typeof BudgetSimulationListItemSchema>;

export const BudgetSimulationDetailSchema = z.object({
  id: z.number(),
  name: z.string(),
  expense_name: z.string(),
  expense_amount_pln: z.number(),
  expense_type: z.enum(["one_time", "recurring"]),
  expense_start_date: z.string(),
  status: z.enum(["pending", "processing", "done", "failed"]),
  result: z.object({
    projection: z.array(SimulationMonthlyPointSchema),
    goal_impacts: z.array(z.object({
      goal_id: z.number(),
      goal_name: z.string(),
      baseline_completion_date: z.string().nullable(),
      simulated_completion_date: z.string().nullable(),
      delay_months: z.number(),
    })),
    ai_summary: z.string(),
    ai_implications: z.string(),
    ai_suggestions: z.array(z.object({
      description: z.string(),
      monthly_saving_pln: z.number(),
      months_required: z.number(),
    })),
  }).nullable(),
  error_message: z.string().nullable(),
  created_at: z.string(),
});
export type BudgetSimulationDetail = z.infer<typeof BudgetSimulationDetailSchema>;

export const AIRecommendationsResponseSchema = z.object({
  insights: z.array(z.object({
    title: z.string(),
    body: z.string(),
    amount_pln: z.number().nullable(),
    insight_type: z.enum(["saving_opportunity", "goal_advice", "warning", "general"]),
  })),
  generated_at: z.string().nullable(),
  data_through_date: z.string().nullable(),
  months_of_data: z.number(),
  has_sufficient_data: z.boolean(),
});
export type AIRecommendationsResponse = z.infer<typeof AIRecommendationsResponseSchema>;

export const EmergencyAdvisorResponseSchema = z.object({
  amount_pln: z.number(),
  fully_coverable_by_cuts: z.boolean(),
  discretionary_cuts: z.array(z.object({
    category_name: z.string(),
    classification: z.string(),
    avg_monthly_spend_pln: z.number(),
    suggested_cut_pln: z.number(),
    months_to_cover: z.number(),
  })),
  total_cuttable_pln: z.number(),
  goal_impacts: z.array(z.object({
    goal_id: z.number(),
    goal_name: z.string(),
    monthly_allocation_pln: z.number(),
    impact_description: z.string(),
  })),
  recovery_months: z.number().nullable(),
  narrative: z.string(),
});
export type EmergencyAdvisorResponse = z.infer<typeof EmergencyAdvisorResponseSchema>;

export const SimulationTaskResponseSchema = z.object({
  task_id: z.string(),
  simulation_id: z.number(),
});
export type SimulationTaskResponse = z.infer<typeof SimulationTaskResponseSchema>;

export const VersionInfoSchema = z.object({
  version: z.string(),
  component: z.string(),
});
export type VersionInfo = z.infer<typeof VersionInfoSchema>;
