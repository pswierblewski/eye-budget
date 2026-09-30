import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AutoConfirmReasonsPanel } from "./AutoConfirmReasonsPanel";

describe("AutoConfirmReasonsPanel", () => {
  it("lists blocking and informational reasons", () => {
    render(
      <AutoConfirmReasonsPanel
        reasons={[
          { code: "sum_mismatch", message: "Suma produktów 47,30 zł ≠ 49,99 zł", blocking: true },
          { code: "vendor_new", message: "Pierwszy paragon ze sklepu „Lidl”", blocking: false },
        ]}
      />
    );

    expect(screen.getByText("Dlaczego nie potwierdzono automatycznie")).toBeInTheDocument();
    expect(screen.getByText("Suma produktów 47,30 zł ≠ 49,99 zł")).toBeInTheDocument();
    expect(screen.getByText("Pierwszy paragon ze sklepu „Lidl”")).toBeInTheDocument();
  });

  it("renders nothing when there are no blocking reasons", () => {
    const { container } = render(
      <AutoConfirmReasonsPanel reasons={[{ code: "vendor_new", message: "x", blocking: false }]} />
    );

    expect(container).toBeEmptyDOMElement();
  });
});
