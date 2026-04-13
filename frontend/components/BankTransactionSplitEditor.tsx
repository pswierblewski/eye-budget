"use client";

import { useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { X, Plus } from "lucide-react";
import { CategoryDropdown } from "@/components/CategoryDropdown";
import { saveBankTransactionSplits, deleteBankTransactionSplits } from "@/lib/api";
import { BankTransactionSplit } from "@/lib/types";

interface SplitRow {
  id: number;
  category_id: number | null;
  amount: string;
}

interface BankTransactionSplitEditorProps {
  readonly txId: number;
  readonly txAmount: number;
  readonly splits: BankTransactionSplit[] | null | undefined;
  readonly onSuccess: () => void;
}

function initRows(splits: BankTransactionSplit[] | null | undefined, nextId: () => number): SplitRow[] {
  if (splits && splits.length > 0) {
    return splits.map((s) => ({
      id: nextId(),
      category_id: s.category_id,
      amount: String(s.amount),
    }));
  }
  return [
    { id: nextId(), category_id: null, amount: "" },
    { id: nextId(), category_id: null, amount: "" },
  ];
}

export function BankTransactionSplitEditor({
  txId,
  txAmount,
  splits,
  onSuccess,
}: BankTransactionSplitEditorProps) {
  const queryClient = useQueryClient();
  const rowIdCounter = useRef(0);
  const nextRowId = () => rowIdCounter.current++;
  const [rows, setRows] = useState<SplitRow[]>(() => initRows(splits, nextRowId));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const hasSavedSplits = !!(splits && splits.length > 0);

  function updateCategory(index: number, category_id: number) {
    setRows((prev) =>
      prev.map((row, i) => (i === index ? { ...row, category_id } : row))
    );
  }

  function updateAmount(index: number, amount: string) {
    setRows((prev) =>
      prev.map((row, i) => (i === index ? { ...row, amount } : row))
    );
  }

  function addRow() {
    setRows((prev) => [...prev, { id: nextRowId(), category_id: null, amount: "" }]);
  }

  function removeRow(index: number) {
    setRows((prev) => prev.filter((_, i) => i !== index));
  }

  function validate(): string | null {
    if (rows.length < 2) {
      return "Podział musi zawierać co najmniej 2 wiersze.";
    }
    for (let i = 0; i < rows.length; i++) {
      if (rows[i].category_id === null) {
        return `Wiersz ${i + 1}: wybierz kategorię.`;
      }
      const val = Number.parseFloat(rows[i].amount);
      if (Number.isNaN(val) || val <= 0) {
        return `Wiersz ${i + 1}: podaj prawidłową kwotę (liczba dodatnia).`;
      }
    }
    const sumCents = rows.reduce(
      (acc, r) => acc + Math.round(Number.parseFloat(r.amount) * 100),
      0
    );
    const expectedCents = Math.round(txAmount * 100);
    if (sumCents !== expectedCents) {
      const sumDisplay = (sumCents / 100).toFixed(2);
      const expectedDisplay = (expectedCents / 100).toFixed(2);
      return `Suma kwot (${sumDisplay} PLN) musi być równa kwocie transakcji (${expectedDisplay} PLN).`;
    }
    return null;
  }

  async function handleSave() {
    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setSaving(true);
    try {
      await saveBankTransactionSplits(
        txId,
        rows.map((r) => {
          if (r.category_id === null) throw new Error("Unexpected null category_id after validation");
          return { category_id: r.category_id, amount: Number.parseFloat(r.amount) };
        })
      );
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", txId] });
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd zapisu podziału.");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    setError(null);
    setDeleting(true);
    try {
      await deleteBankTransactionSplits(txId);
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", txId] });
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Błąd usunięcia podziału.");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-3">
      {/* Rows */}
      <div className="space-y-2">
        {rows.map((row, i) => (
          <div key={row.id} className="flex items-start gap-2">
            {/* Category dropdown */}
            <div className="flex-1 min-w-0">
              <CategoryDropdown
                value={row.category_id ?? undefined}
                onChange={(id) => updateCategory(i, id)}
              />
            </div>

            {/* Amount input */}
            <div className="w-32 shrink-0">
              <input
                type="number"
                step="0.01"
                min="0"
                value={row.amount}
                onChange={(e) => updateAmount(i, e.target.value)}
                placeholder="0.00"
                className="w-full text-sm border border-indigo-200 rounded-md px-2 py-1
                  bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-[#635bff]
                  text-gray-900 mt-1"
              />
            </div>

            {/* PLN label */}
            <span className="text-xs text-gray-500 mt-2.5 shrink-0">PLN</span>

            {/* Remove row button */}
            <button
              type="button"
              onClick={() => removeRow(i)}
              disabled={rows.length <= 2}
              className="mt-1.5 p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600
                disabled:opacity-30 disabled:cursor-not-allowed transition-colors shrink-0"
              title="Usuń wiersz"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>

      {/* Add row button */}
      <button
        type="button"
        onClick={addRow}
        className="flex items-center gap-1 text-xs text-[#635bff] hover:text-[#4f46e5]
          py-1 px-1 hover:bg-indigo-50 rounded transition-colors"
      >
        <Plus size={13} />
        Dodaj wiersz
      </button>

      {/* Validation / error message */}
      {error && (
        <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-md px-2 py-1.5">
          {error}
        </p>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          onClick={handleSave}
          disabled={saving || deleting}
          className="flex-1 text-xs font-medium py-1.5 px-3 rounded-md bg-[#635bff]
            text-white disabled:opacity-40 disabled:cursor-not-allowed
            hover:bg-[#4f46e5] transition-colors"
        >
          {saving ? "Zapisywanie…" : "Zapisz podział"}
        </button>

        {hasSavedSplits && (
          <button
            type="button"
            onClick={handleDelete}
            disabled={saving || deleting}
            className="flex-1 text-xs font-medium py-1.5 px-3 rounded-md border
              border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-40
              disabled:cursor-not-allowed transition-colors"
          >
            {deleting ? "Usuwanie…" : "Usuń podział"}
          </button>
        )}
      </div>
    </div>
  );
}
