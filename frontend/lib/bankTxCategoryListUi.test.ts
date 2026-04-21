/** @vitest-environment node */
import { describe, expect, it } from "vitest";
import { shouldShowAiCategoryProposal } from "./bankTxCategoryListUi";
import type { BankTransactionListItem } from "./types";

const base = (): BankTransactionListItem => ({
  id: 1,
  reference_number: "r",
  booking_date: "2026-04-20",
  counterparty: null,
  description: null,
  amount: -1,
  currency: "PLN",
  operation_type: null,
  category_id: null,
  category_name: null,
});

describe("shouldShowAiCategoryProposal", () => {
  it("false when receipt category present", () => {
    const tx = {
      ...base(),
      receipt_category_name: "Food",
      ai_top_candidate: { category_id: 1, category_name: "X", category_score: 0.9 },
    };
    expect(shouldShowAiCategoryProposal(tx)).toBe(false);
  });

  it("false when split multi-category", () => {
    const tx = {
      ...base(),
      split_category_name: "A",
      split_count: 2,
      ai_top_candidate: { category_id: 1, category_name: "X", category_score: 0.9 },
    };
    expect(shouldShowAiCategoryProposal(tx)).toBe(false);
  });

  it("false when user category name set", () => {
    const tx = {
      ...base(),
      category_name: "Assigned",
      ai_top_candidate: { category_id: 1, category_name: "X", category_score: 0.9 },
    };
    expect(shouldShowAiCategoryProposal(tx)).toBe(false);
  });

  it("false when category_id set", () => {
    const tx = {
      ...base(),
      category_id: 9,
      category_name: null,
      ai_top_candidate: { category_id: 1, category_name: "X", category_score: 0.9 },
    };
    expect(shouldShowAiCategoryProposal(tx)).toBe(false);
  });

  it("false when no ai_top_candidate", () => {
    expect(shouldShowAiCategoryProposal(base())).toBe(false);
  });

  it("true when unassigned and ai_top_candidate present", () => {
    const tx = {
      ...base(),
      ai_top_candidate: { category_id: 2, category_name: "Jedzenie", category_score: 0.87 },
    };
    expect(shouldShowAiCategoryProposal(tx)).toBe(true);
  });
});
