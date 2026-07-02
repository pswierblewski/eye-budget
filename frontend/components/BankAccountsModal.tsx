"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listBankAccounts,
  createBankAccount,
  updateBankAccount,
  deleteBankAccount,
} from "@/lib/api";
import { BankAccountStats } from "@/lib/types";
import { Button, SectionLabel, Modal } from "@/components/ui";
import { MutationErrorNotice, QueryState } from "@/components/QueryState";
import { Pencil, Trash2, X } from "lucide-react";

const BANK_TYPE_OPTIONS = [
  { value: "pekao", label: "Pekao SA" },
  { value: "revolut", label: "Revolut" },
  { value: "other", label: "Inne" },
];

const COLOR_OPTIONS = [
  { value: "blue", label: "Niebieski" },
  { value: "green", label: "Zielony" },
  { value: "purple", label: "Fioletowy" },
  { value: "orange", label: "Pomarańczowy" },
  { value: "red", label: "Czerwony" },
];

const COLOR_CLASSES: Record<string, string> = {
  blue: "bg-blue-500",
  green: "bg-green-500",
  purple: "bg-purple-500",
  orange: "bg-orange-500",
  red: "bg-red-500",
};

type EditState = { id: number; name: string; color: string } | null;

type Props = {
  open: boolean;
  onClose: () => void;
};

export function BankAccountsModal({ open, onClose }: Props) {
  const queryClient = useQueryClient();
  const [addName, setAddName] = useState("");
  const [addBankType, setAddBankType] = useState("pekao");
  const [addColor, setAddColor] = useState("blue");
  const [editState, setEditState] = useState<EditState>(null);

  const accountsQuery = useQuery({
    queryKey: ["bank-accounts"],
    queryFn: listBankAccounts,
    enabled: open,
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["bank-accounts"] });
  };

  const createMutation = useMutation({
    mutationFn: () =>
      createBankAccount({ name: addName, bank_type: addBankType, color: addColor }),
    onSuccess: () => {
      invalidate();
      setAddName("");
      setAddBankType("pekao");
      setAddColor("blue");
    },
  });

  const updateMutation = useMutation({
    mutationFn: (acc: EditState) =>
      updateBankAccount(acc!.id, { name: acc!.name, color: acc!.color }),
    onSuccess: () => {
      invalidate();
      setEditState(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBankAccount,
    onSuccess: invalidate,
  });

  if (!open) return null;

  return (
    <Modal open={open} onClose={onClose} maxWidth="lg">
      <div className="p-6 flex flex-col gap-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-gray-900">
            Zarządzaj kontami bankowymi
          </h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-gray-100">
            <X className="h-4 w-4 text-gray-500" />
          </button>
        </div>

        <MutationErrorNotice mutation={createMutation} />
        <MutationErrorNotice mutation={updateMutation} />
        <MutationErrorNotice mutation={deleteMutation} />

        {/* Account list */}
        <QueryState query={accountsQuery} errorTitle="Nie udało się pobrać kont.">
          {(accounts: BankAccountStats[]) => (
            <div className="space-y-2">
              {accounts.length === 0 && (
                <p className="text-sm text-gray-400 italic">Brak kont.</p>
              )}
              {accounts.map((acc) =>
                editState?.id === acc.id ? (
                  <div key={acc.id} className="flex items-center gap-2 p-2 border rounded-lg">
                    <input
                      className="flex-1 border rounded px-2 py-1 text-sm"
                      value={editState.name}
                      onChange={(e) =>
                        setEditState({ ...editState, name: e.target.value })
                      }
                    />
                    <select
                      className="border rounded px-2 py-1 text-sm"
                      value={editState.color}
                      onChange={(e) =>
                        setEditState({ ...editState, color: e.target.value })
                      }
                    >
                      {COLOR_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={updateMutation.isPending}
                      onClick={() => updateMutation.mutate(editState)}
                    >
                      Zapisz
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setEditState(null)}
                    >
                      Anuluj
                    </Button>
                  </div>
                ) : (
                  <div
                    key={acc.id}
                    className="flex items-center gap-3 p-2 border rounded-lg"
                  >
                    <span
                      className={`w-3 h-3 rounded-full shrink-0 ${COLOR_CLASSES[acc.color] ?? "bg-gray-400"}`}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-800 truncate">
                        {acc.name}
                      </p>
                      <p className="text-xs text-gray-400">
                        {BANK_TYPE_OPTIONS.find((o) => o.value === acc.bank_type)?.label ??
                          acc.bank_type}
                        {" · "}
                        {acc.transaction_count} transakcji
                      </p>
                    </div>
                    <button
                      className="p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-700"
                      onClick={() =>
                        setEditState({ id: acc.id, name: acc.name, color: acc.color })
                      }
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      className={`p-1 rounded text-gray-400 ${
                        acc.transaction_count > 0
                          ? "opacity-40 cursor-not-allowed"
                          : "hover:bg-red-50 hover:text-red-600"
                      }`}
                      disabled={acc.transaction_count > 0 || deleteMutation.isPending}
                      title={
                        acc.transaction_count > 0
                          ? "Nie można usunąć konta z transakcjami"
                          : "Usuń konto"
                      }
                      onClick={() => deleteMutation.mutate(acc.id)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )
              )}
            </div>
          )}
        </QueryState>

        {/* Add account form */}
        <div className="border-t pt-4">
          <SectionLabel className="mb-2">Dodaj nowe konto</SectionLabel>
          <div className="flex flex-col gap-2">
            <input
              className="border rounded px-2 py-1.5 text-sm w-full"
              placeholder="Nazwa konta (np. Pekao SA Główne)"
              value={addName}
              onChange={(e) => setAddName(e.target.value)}
            />
            <div className="flex gap-2">
              <select
                className="flex-1 border rounded px-2 py-1.5 text-sm"
                value={addBankType}
                onChange={(e) => setAddBankType(e.target.value)}
              >
                {BANK_TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <select
                className="flex-1 border rounded px-2 py-1.5 text-sm"
                value={addColor}
                onChange={(e) => setAddColor(e.target.value)}
              >
                {COLOR_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <Button
              variant="primary"
              size="sm"
              disabled={!addName.trim() || createMutation.isPending}
              onClick={() => createMutation.mutate()}
              className="self-end"
            >
              {createMutation.isPending ? "Dodawanie…" : "Dodaj konto"}
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
}
