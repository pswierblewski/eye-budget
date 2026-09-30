/** @vitest-environment node */
import { describe, expect, it } from "vitest";
import { categorySourceLabel } from "./categorySource";

describe("categorySourceLabel", () => {
  it("labels history with count", () => {
    expect(categorySourceLabel({ source: "history", history_count: 14 })).toBe("z historii (14×)");
  });

  it("labels AI with fraction score as percent", () => {
    expect(categorySourceLabel({ source: "ai", topScore: 0.62 })).toBe("AI · 62%");
  });

  it("labels AI with percent score", () => {
    expect(categorySourceLabel({ source: "ai", topScore: 91 })).toBe("AI · 91%");
  });

  it("labels AI without score", () => {
    expect(categorySourceLabel({ source: "ai", topScore: null })).toBe("AI");
  });

  it("returns null for legacy candidates", () => {
    expect(categorySourceLabel({})).toBeNull();
  });
});
