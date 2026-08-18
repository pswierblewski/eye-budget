/** @vitest-environment node */
import { describe, expect, it } from "vitest";
import {
  BankTransactionListItemSchema,
  paginatedSchema,
} from "./types";

const listSchema = paginatedSchema(BankTransactionListItemSchema);

const baseItem = {
  id: 1,
  reference_number: "REF-001",
  booking_date: "2026-08-18",
  counterparty: null,
  description: null,
  amount: -42.5,
  currency: "PLN",
  operation_type: null,
  category_id: null,
  category_name: null,
};

describe("BankTransactionListItemSchema (paginated)", () => {
  it("parses ai_top_candidate: null (post-import, pre-categorization)", () => {
    const payload = {
      items: [{ ...baseItem, ai_top_candidate: null }],
      total: 1,
      limit: 50,
      offset: 0,
    };

    const result = listSchema.parse(payload);

    expect(result.items).toHaveLength(1);
    expect(result.items[0].ai_top_candidate).toBeNull();
  });

  it("parses ai_top_candidate object", () => {
    const payload = {
      items: [
        {
          ...baseItem,
          ai_top_candidate: {
            category_id: 2,
            category_name: "Jedzenie",
            category_score: 0.87,
          },
        },
      ],
      total: 1,
      limit: 50,
      offset: 0,
    };

    const result = listSchema.parse(payload);

    expect(result.items[0].ai_top_candidate).toEqual({
      category_id: 2,
      category_name: "Jedzenie",
      category_score: 0.87,
    });
  });

  it("parses missing ai_top_candidate field", () => {
    const payload = {
      items: [baseItem],
      total: 1,
      limit: 50,
      offset: 0,
    };

    const result = listSchema.parse(payload);

    expect(result.items[0].ai_top_candidate).toBeUndefined();
  });
});
