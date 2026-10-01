import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RescoreReceiptsModal } from "./RescoreReceiptsModal";

const handlers: Record<string, (data: unknown) => void> = {};
const bind = vi.fn((event: string, cb: (data: unknown) => void) => {
  handlers[event] = cb;
});
const channel = { bind, unbind_all: vi.fn(), unsubscribe: vi.fn() };

vi.mock("@/lib/pusher", () => ({ getPusher: () => ({ subscribe: () => channel }) }));
const rescore = vi.fn();
vi.mock("@/lib/api", () => ({ rescorePendingReceipts: (dry: boolean) => rescore(dry) }));

function renderModal(onFinished = vi.fn()) {
  const client = new QueryClient();
  render(
    <QueryClientProvider client={client}>
      <RescoreReceiptsModal open onClose={vi.fn()} onFinished={onFinished} />
    </QueryClientProvider>
  );
  return onFinished;
}

describe("RescoreReceiptsModal", () => {
  beforeEach(() => {
    rescore.mockReset();
    bind.mockClear();
    for (const k of Object.keys(handlers)) delete handlers[k];
  });

  it("runs dry run, shows report, then confirms", async () => {
    rescore.mockResolvedValueOnce({ task_id: "dry" }).mockResolvedValueOnce({ task_id: "real" });
    const onFinished = renderModal();

    await userEvent.click(screen.getByRole("button", { name: "Sprawdź auto-potwierdzenie" }));
    expect(rescore).toHaveBeenCalledWith(true);

    await waitFor(() => expect(bind).toHaveBeenCalledTimes(3));
    handlers["receipt.rescore_done"]({
      task_id: "dry",
      report: {
        dry_run: true,
        total: 47,
        eligible: 32,
        confirmed: 0,
        skipped: 0,
        errors: 0,
        top_reasons: [{ code: "low_confidence", message: "Nowy produkt „X”: pewność AI 62%", count: 9 }],
      },
    });

    expect(await screen.findByText("32 z 47 paragonów potwierdziłoby się automatycznie.")).toBeInTheDocument();
    expect(screen.getByText("Nowy produkt „X”: pewność AI 62% — 9×")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Potwierdź automatycznie 32" }));
    expect(rescore).toHaveBeenLastCalledWith(false);

    await waitFor(() => expect(bind).toHaveBeenCalledTimes(6));
    handlers["receipt.rescore_done"]({
      task_id: "real",
      report: { dry_run: false, total: 47, eligible: 32, confirmed: 31, skipped: 1, errors: 0, top_reasons: [] },
    });

    expect(await screen.findByText("Potwierdzono automatycznie 31 paragonów.")).toBeInTheDocument();
    expect(onFinished).toHaveBeenCalled();
  });
});
