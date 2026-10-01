/** @vitest-environment node */
import { describe, expect, it } from "vitest";
import {
  ReceiptScanDetailSchema,
  ReceiptScanListItemSchema,
  RescoreReportSchema,
  SaveReviewResponseSchema,
  SingleAutoConfirmResultSchema,
} from "./types";

const baseDetail = {
  id: 1,
  filename: "a.jpg",
  status: "to_confirm",
  result: null,
  categories_candidates: {
    category_candidates: [
      {
        product_name: "MLEKO",
        category_candidates: [{ category_id: 1, category_name: "Nabiał", category_score: 0.93 }],
        source: "history",
        product_id: 10,
        history_count: 14,
      },
    ],
  },
  minio_object_key: null,
  transaction: null,
};

describe("receipt auto-confirm schemas", () => {
  it("parses candidate source metadata and reasons", () => {
    const parsed = ReceiptScanDetailSchema.parse({
      ...baseDetail,
      confirmation_source: null,
      auto_confirm_reasons: [{ code: "sum_mismatch", message: "Suma produktów 1,00 zł ≠ 2,00 zł", blocking: true }],
    });

    expect(parsed.categories_candidates?.category_candidates[0].source).toBe("history");
    expect(parsed.categories_candidates?.category_candidates[0].history_count).toBe(14);
    expect(parsed.auto_confirm_reasons?.[0].blocking).toBe(true);
  });

  it("parses legacy detail without new fields", () => {
    const legacy = {
      ...baseDetail,
      categories_candidates: {
        category_candidates: [
          { product_name: "MLEKO", category_candidates: [{ category_id: 1, category_name: "Nabiał", category_score: 0.9 }] },
        ],
      },
    };

    const parsed = ReceiptScanDetailSchema.parse(legacy);

    expect(parsed.confirmation_source).toBeUndefined();
    expect(parsed.categories_candidates?.category_candidates[0].source).toBeUndefined();
  });

  it("parses list item confirmation_source", () => {
    const parsed = ReceiptScanListItemSchema.parse({
      id: 1,
      filename: "a.jpg",
      status: "done",
      vendor: null,
      date: null,
      total: null,
      confirmation_source: "auto",
    });

    expect(parsed.confirmation_source).toBe("auto");
  });

  it("parses rescore report", () => {
    const parsed = RescoreReportSchema.parse({
      dry_run: true,
      total: 47,
      eligible: 32,
      confirmed: 0,
      skipped: 1,
      errors: 0,
      top_reasons: [{ code: "low_confidence", message: "Nowy produkt „X”: pewność AI 62%", count: 9 }],
    });

    expect(parsed.eligible).toBe(32);
  });

  it("parses save-review response with selections and waivers", () => {
    const parsed = SaveReviewResponseSchema.parse({
      receipt: {
        ...baseDetail,
        category_selections: { MLEKO: 1 },
        auto_confirm_waivers: [{ code: "sum_mismatch" }],
      },
      auto_confirm: {
        dry_run: true,
        ok: false,
        confirmed: false,
        reasons: [{ code: "sum_mismatch", message: "Suma", blocking: true }],
      },
    });

    expect(parsed.receipt.category_selections?.MLEKO).toBe(1);
    expect(parsed.receipt.auto_confirm_waivers?.[0].code).toBe("sum_mismatch");
  });

  it("parses single auto-confirm result", () => {
    const parsed = SingleAutoConfirmResultSchema.parse({
      dry_run: true,
      ok: false,
      confirmed: false,
      reasons: [{ code: "vendor_new", message: "Nowy sprzedawca", blocking: true }],
      receipt: null,
    });

    expect(parsed.ok).toBe(false);
    expect(parsed.reasons[0].blocking).toBe(true);
  });
});
