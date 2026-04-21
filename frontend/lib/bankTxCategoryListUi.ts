import type { BankTransactionListItem } from "@/lib/types";

/**
 * Whether the list row should show AI top proposal + save button (spec 2026-04-20).
 */
export function shouldShowAiCategoryProposal(tx: BankTransactionListItem): boolean {
  if (tx.category_id != null) return false;
  if (tx.receipt_category_name) return false;
  if ((tx.split_count ?? 0) >= 2) return false;
  if (tx.category_name != null && tx.category_name !== "") return false;
  if (!tx.ai_top_candidate) return false;
  return true;
}
