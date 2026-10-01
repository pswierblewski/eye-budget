import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

  it("calls onAccept with code when Akceptuj is clicked", async () => {
    const user = userEvent.setup();
    const onAccept = vi.fn();

    render(
      <AutoConfirmReasonsPanel
        reasons={[
          {
            code: "low_confidence",
            message: "Nowy produkt „X”",
            blocking: true,
            product_name: "X",
          },
        ]}
        onAccept={onAccept}
      />
    );

    await user.click(screen.getByRole("button", { name: "Akceptuj" }));

    expect(onAccept).toHaveBeenCalledWith({ code: "low_confidence", product_name: "X" });
  });

  it("shows Zaakceptowano for waived reasons", () => {
    render(
      <AutoConfirmReasonsPanel
        reasons={[
          {
            code: "sum_mismatch",
            message: "Suma",
            blocking: false,
          },
        ]}
        waivers={[{ code: "sum_mismatch" }]}
      />
    );

    expect(screen.getByText("Zaakceptowano")).toBeInTheDocument();
  });
});
