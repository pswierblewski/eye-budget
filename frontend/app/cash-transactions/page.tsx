"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listCashTransactions,
  createCashTransaction,
  confirmCashTransaction,
  reopenCashTransaction,
  deleteCashTransaction,
  updateCashTransaction,
  getCashReceiptCandidates,
  linkCashToReceipt,
  unlinkCashTransaction,
  getCashTransactionCounts,
  updateCashTransactionTags,
  getAllTags,
  listVendors,
} from "@/lib/api";
import {
  CashTransactionListItem,
  CashTransactionCreate,
  ReceiptCandidateItem,
  VendorItem,
} from "@/lib/types";
import { CategoryDropdown } from "@/components/CategoryDropdown";
import { VendorDropdown } from "@/components/VendorDropdown";
import { StatusBadge } from "@/components/StatusBadge";
import TagsEditor from "@/components/TagsEditor";
import { DataTable, Column } from "@/components/DataTable";
import Link from "next/link";
import { Plus, Banknote, Receipt, Trash2 } from "lucide-react";

const STATUS_FILTERS = ["all", "to_confirm", "done"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

function formatAmount(amount: number, currency: string): string {
  return new Intl.NumberFormat("pl-PL", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

function MatchBadge({ score }: { score: number }) {
  const labels: Record<number, string> = {
    2: "kwota + data",
    3: "kwota + data + sklep",
  };
  const colors: Record<number, string> = {
    2: "bg-yellow-100 text-yellow-700",
    3: "bg-green-100 text-green-700",
  };
  return (
    <span
      className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
        colors[score] ?? "bg-gray-100 text-gray-500"
      }`}
    >
      {labels[score] ?? `score ${score}`}
    </span>
  );
}

function SourceBadge({ source }: { source: string }) {
  if (source === "receipt") {
    return (
      <span className="flex items-center gap-1 text-[10px] bg-blue-50 text-blue-700 border border-blue-200 rounded-full px-2 py-0.5 font-medium">
        <Receipt className="h-3 w-3" />
        Paragon
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-[10px] bg-gray-50 text-gray-600 border border-gray-200 rounded-full px-2 py-0.5 font-medium">
      <Banknote className="h-3 w-3" />
      Ręcznie
    </span>
  );
}

// ---------------------------------------------------------------------------
// Add Transaction Modal
// ---------------------------------------------------------------------------
function AddTransactionModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const today = new Date().toISOString().split("T")[0];
  const [date, setDate] = useState(today);
  const [amountStr, setAmountStr] = useState("");
  const [isExpense, setIsExpense] = useState(true);
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [vendorName, setVendorName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: vendors = [] } = useQuery<VendorItem[]>({
    queryKey: ["vendors"],
    queryFn: listVendors,
  });

  const createMutation = useMutation({
    mutationFn: (data: CashTransactionCreate) => createCashTransaction(data),
    onSuccess: () => {
      onSuccess();
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const parsed = parseFloat(amountStr.replace(",", "."));
    if (isNaN(parsed) || parsed <= 0) {
      setError("Podaj prawidłową kwotę (liczbę dodatnią).");
      return;
    }
    const amount = isExpense ? -parsed : parsed;
    const matchedVendor = vendors.find(
      (v) => v.name.toLowerCase() === vendorName.trim().toLowerCase()
    );
    createMutation.mutate({
      booking_date: date,
      amount,
      description: description || null,
      category_id: categoryId ?? null,
      vendor_id: matchedVendor?.id ?? null,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-base font-semibold text-gray-800 mb-4">
          Nowa transakcja gotówkowa
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Date */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Data
            </label>
            <input
              type="date"
              required
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#635bff]/30"
            />
          </div>

          {/* Amount */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Kwota
            </label>
            <div className="flex gap-2 items-center">
              <div className="flex rounded-md border border-gray-300 overflow-hidden text-xs font-medium">
                <button
                  type="button"
                  onClick={() => setIsExpense(true)}
                  className={`px-3 py-2 ${isExpense ? "bg-red-50 text-red-600" : "bg-white text-gray-500 hover:bg-gray-50"}`}
                >
                  Wydatek
                </button>
                <button
                  type="button"
                  onClick={() => setIsExpense(false)}
                  className={`px-3 py-2 ${!isExpense ? "bg-green-50 text-green-600" : "bg-white text-gray-500 hover:bg-gray-50"}`}
                >
                  Przychód
                </button>
              </div>
              <input
                type="text"
                required
                inputMode="decimal"
                placeholder="0.00"
                value={amountStr}
                onChange={(e) => setAmountStr(e.target.value)}
                className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#635bff]/30"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Opis (opcjonalny)
            </label>
            <textarea
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="np. Kawa w kawiarni"
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#635bff]/30 resize-none"
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Kategoria (opcjonalna)
            </label>
            <CategoryDropdown value={categoryId} onChange={setCategoryId} />
          </div>

          {/* Vendor */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Sklep / sprzedawca (opcjonalny)
            </label>
            <VendorDropdown value={vendorName} onChange={setVendorName} />
          </div>

          {error && (
            <p className="text-xs text-red-600">{error}</p>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-md border border-gray-300 text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              Anuluj
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="flex-1 px-4 py-2 rounded-md bg-[#635bff] text-white text-sm font-medium hover:bg-[#4b44cc] transition-colors disabled:opacity-50"
            >
              {createMutation.isPending ? "Zapisywanie…" : "Dodaj"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Expanded row
// ---------------------------------------------------------------------------
type ExpandedRowProps = {
  tx: CashTransactionListItem;
  allTags?: string[];
};

function ExpandedRowContent({ tx, allTags = [] }: ExpandedRowProps) {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<number | undefined>(
    tx.category_id ?? undefined
  );
  const [showCandidates, setShowCandidates] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  // Edit state
  const [editMode, setEditMode] = useState(false);
  const [editDate, setEditDate] = useState(tx.booking_date);
  const [editAmountStr, setEditAmountStr] = useState(String(Math.abs(tx.amount)));
  const [editIsExpense, setEditIsExpense] = useState(tx.amount <= 0);
  const [editDescription, setEditDescription] = useState(tx.description ?? "");
  const [editVendorName, setEditVendorName] = useState(tx.vendor_name ?? "");

  const { data: vendors = [] } = useQuery<VendorItem[]>({
    queryKey: ["vendors"],
    queryFn: listVendors,
    enabled: editMode,
  });

  const { data: detail } = useQuery({
    queryKey: ["cash-transaction", tx.id],
    queryFn: () =>
      fetch(`/api/cash-transactions/${tx.id}`).then((r) => r.json()),
  });

  const { data: candidates = [], isFetching: candidatesLoading } = useQuery<ReceiptCandidateItem[]>({
    queryKey: ["cash-tx-receipt-candidates", tx.id],
    queryFn: () => getCashReceiptCandidates(tx.id),
    enabled: showCandidates,
  });

  const confirmMutation = useMutation({
    mutationFn: (categoryId: number) => confirmCashTransaction(tx.id, categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["cash-transactions-counts"] });
    },
  });

  const reopenMutation = useMutation({
    mutationFn: () => reopenCashTransaction(tx.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["cash-transaction", tx.id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteCashTransaction(tx.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["cash-transactions-counts"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: () => {
      const parsed = parseFloat(editAmountStr.replace(",", "."));
      const amount = editIsExpense ? -Math.abs(parsed) : Math.abs(parsed);
      const matchedVendor = vendors.find(
        (v) => v.name.toLowerCase() === editVendorName.trim().toLowerCase()
      );
      return updateCashTransaction(tx.id, {
        booking_date: editDate,
        amount,
        description: editDescription || null,
        vendor_id: matchedVendor?.id ?? null,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["cash-transaction", tx.id] });
      setEditMode(false);
    },
  });

  const linkMutation = useMutation({
    mutationFn: (receiptTxId: number) => linkCashToReceipt(tx.id, receiptTxId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-transaction", tx.id] });
      queryClient.invalidateQueries({ queryKey: ["cash-tx-receipt-candidates", tx.id] });
      setShowCandidates(false);
    },
  });

  const unlinkMutation = useMutation({
    mutationFn: () => unlinkCashTransaction(tx.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-transaction", tx.id] });
    },
  });

  const tagsMutation = useMutation({
    mutationFn: (tags: string[]) => updateCashTransactionTags(tx.id, tags),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["cash-transaction", tx.id] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const receiptLink = detail?.receipt_link ?? null;

  return (
    <div className="flex gap-8">
      {/* Left: details / edit form */}
      <div className="flex-1 space-y-3">
        {editMode ? (
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-500 mb-1">Data</label>
                <input
                  type="date"
                  value={editDate}
                  onChange={(e) => setEditDate(e.target.value)}
                  className="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm"
                />
              </div>
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-500 mb-1">Kwota</label>
                <div className="flex gap-1.5 items-center">
                  <div className="flex rounded border border-gray-300 overflow-hidden text-xs">
                    <button
                      type="button"
                      onClick={() => setEditIsExpense(true)}
                      className={`px-2 py-1.5 ${editIsExpense ? "bg-red-50 text-red-600" : "bg-white text-gray-400"}`}
                    >−</button>
                    <button
                      type="button"
                      onClick={() => setEditIsExpense(false)}
                      className={`px-2 py-1.5 ${!editIsExpense ? "bg-green-50 text-green-600" : "bg-white text-gray-400"}`}
                    >+</button>
                  </div>
                  <input
                    type="text"
                    value={editAmountStr}
                    onChange={(e) => setEditAmountStr(e.target.value)}
                    className="flex-1 border border-gray-300 rounded-md px-2 py-1.5 text-sm"
                  />
                </div>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Opis</label>
              <textarea
                rows={2}
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                className="w-full border border-gray-300 rounded-md px-2 py-1.5 text-sm resize-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Sklep / sprzedawca</label>
              <VendorDropdown value={editVendorName} onChange={setEditVendorName} />
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => updateMutation.mutate()}
                disabled={updateMutation.isPending}
                className="px-3 py-1.5 rounded-md bg-[#635bff] text-white text-xs font-medium disabled:opacity-50"
              >
                {updateMutation.isPending ? "Zapisywanie…" : "Zapisz"}
              </button>
              <button
                onClick={() => setEditMode(false)}
                className="px-3 py-1.5 rounded-md border border-gray-300 text-xs font-medium hover:bg-gray-50"
              >
                Anuluj
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-1.5 text-xs text-gray-600">
            {tx.description && (
              <div>
                <span className="font-medium text-gray-700">Opis: </span>
                {tx.description}
              </div>
            )}
            {(detail?.vendor_name ?? tx.vendor_name) && (
              <div>
                <span className="font-medium text-gray-700">Sklep: </span>
                {detail?.vendor_name ?? tx.vendor_name}
              </div>
            )}
            <div>
              <span className="font-medium text-gray-700">Źródło: </span>
              {tx.source === "receipt" ? "Paragon" : "Ręcznie wprowadzone"}
            </div>
            {tx.source === "receipt" && detail?.receipt_scan_id && (
              <div>
                <span className="font-medium text-gray-700">Paragon: </span>
                <Link
                  href={`/receipts/${detail.receipt_scan_id}`}
                  className="text-[#635bff] hover:underline"
                >
                  #{detail.receipt_scan_id}
                </Link>
              </div>
            )}
            <button
              onClick={() => setEditMode(true)}
              className="mt-1 text-xs text-[#635bff] hover:underline"
            >
              Edytuj
            </button>
          </div>
        )}

        {/* Tags */}
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Tagi</p>
          <TagsEditor
            tags={tx.tags ?? []}
            allTags={allTags}
            onSave={(tags) => tagsMutation.mutate(tags)}
            isSaving={tagsMutation.isPending}
          />
        </div>
      </div>

      {/* Right: category + confirm/reopen + receipt linking + delete */}
      <div className="w-96 space-y-4">
        {/* Category */}
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Kategoria</p>
          <CategoryDropdown
            value={selectedCategory}
            onChange={setSelectedCategory}
          />
        </div>

        {/* Confirm / reopen */}
        <div className="flex gap-2">
          {tx.status === "to_confirm" ? (
            <button
              disabled={!selectedCategory || confirmMutation.isPending}
              onClick={() => selectedCategory && confirmMutation.mutate(selectedCategory)}
              className="flex-1 px-3 py-1.5 rounded-md bg-[#635bff] text-white text-xs font-medium
                         disabled:opacity-40 hover:bg-[#4b44cc] transition-colors"
            >
              {confirmMutation.isPending ? "Zapisywanie…" : "Potwierdź"}
            </button>
          ) : (
            <button
              disabled={reopenMutation.isPending}
              onClick={() => reopenMutation.mutate()}
              className="flex-1 px-3 py-1.5 rounded-md border border-gray-300 text-xs font-medium
                         hover:bg-gray-50 transition-colors disabled:opacity-40"
            >
              {reopenMutation.isPending ? "…" : "Cofnij potwierdzenie"}
            </button>
          )}
        </div>

        {/* Receipt linking */}
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Paragon</p>
          {receiptLink ? (
            <div className="flex items-center justify-between rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-xs">
              <div>
                <Link
                  href={`/receipts/${receiptLink.scan_id}`}
                  className="font-medium text-[#635bff] hover:underline"
                >
                  {receiptLink.scan_filename}
                </Link>
                <div className="text-gray-500 mt-0.5">
                  {receiptLink.vendor_name} · {receiptLink.date} ·{" "}
                  {receiptLink.total.toFixed(2)} PLN
                </div>
              </div>
              <button
                onClick={() => unlinkMutation.mutate()}
                disabled={unlinkMutation.isPending}
                className="text-gray-400 hover:text-red-500 transition-colors ml-2 shrink-0"
                title="Odlinkuj paragon"
              >
                ✕
              </button>
            </div>
          ) : (
            <div>
              {!showCandidates ? (
                <button
                  onClick={() => setShowCandidates(true)}
                  className="text-xs text-[#635bff] hover:underline"
                >
                  Szukaj pasującego paragonu
                </button>
              ) : (
                <div className="space-y-1.5">
                  {candidatesLoading && (
                    <p className="text-xs text-gray-400">Szukanie…</p>
                  )}
                  {!candidatesLoading && candidates.length === 0 && (
                    <p className="text-xs text-gray-400">Brak pasujących paragonów.</p>
                  )}
                  {candidates.map((c) => (
                    <div
                      key={c.receipt_transaction_id}
                      className="flex items-center justify-between rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-xs"
                    >
                      <div>
                        <span className="font-medium text-gray-700">
                          {c.vendor_name}
                        </span>
                        <span className="text-gray-400 ml-2">
                          {c.date} · {c.total.toFixed(2)} PLN
                        </span>
                        <MatchBadge score={c.match_score} />
                      </div>
                      <button
                        onClick={() => linkMutation.mutate(c.receipt_transaction_id)}
                        disabled={linkMutation.isPending}
                        className="ml-2 px-2 py-1 rounded-md bg-[#635bff] text-white text-[10px] font-medium hover:bg-[#4b44cc] disabled:opacity-40"
                      >
                        Linkuj
                      </button>
                    </div>
                  ))}
                  <button
                    onClick={() => setShowCandidates(false)}
                    className="text-xs text-gray-400 hover:text-gray-600"
                  >
                    Ukryj
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Delete */}
        <div className="pt-2 border-t border-gray-100">
          {showDeleteConfirm ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-red-600">Na pewno usunąć?</span>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="px-2 py-1 rounded-md bg-red-600 text-white text-xs font-medium disabled:opacity-40"
              >
                {deleteMutation.isPending ? "Usuwanie…" : "Usuń"}
              </button>
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-2 py-1 rounded-md border border-gray-300 text-xs font-medium hover:bg-gray-50"
              >
                Anuluj
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowDeleteConfirm(true)}
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-red-500 transition-colors"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Usuń transakcję
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function CashTransactionsPage() {
  const queryClient = useQueryClient();
  const PAGE_SIZE = 50;
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sortBy, setSortBy] = useState("booking_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [showAddModal, setShowAddModal] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["cash-transactions", page, statusFilter, sortBy, sortDir],
    queryFn: () =>
      listCashTransactions({
        page,
        limit: PAGE_SIZE,
        status: statusFilter !== "all" ? statusFilter : undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
      }),
    staleTime: 30_000,
  });
  const transactions = data?.items ?? [];
  const total = data?.total ?? 0;

  const { data: statusCounts = {} } = useQuery({
    queryKey: ["cash-transactions-counts"],
    queryFn: getCashTransactionCounts,
    staleTime: 30_000,
  });
  const totalAll = Object.values(statusCounts).reduce<number>((sum, v) => sum + v, 0);

  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: getAllTags,
    staleTime: 60_000,
  });

  const columns: Column<CashTransactionListItem>[] = [
    {
      header: "Data",
      accessor: "booking_date",
      serverSortKey: "booking_date",
      className: "whitespace-nowrap text-gray-700",
    },
    {
      header: "Opis / sklep",
      accessor: (t) => (
        <div>
          <div className="font-medium text-gray-800 truncate max-w-xs">
            {t.vendor_name ?? t.description ?? "—"}
          </div>
          {t.vendor_name && t.description && (
            <div className="text-xs text-gray-400 truncate mt-0.5 max-w-xs">
              {t.description}
            </div>
          )}
        </div>
      ),
      serverSortKey: "description",
    },
    {
      header: "Kwota",
      accessor: (t) => (
        <span
          className={`font-mono font-medium whitespace-nowrap ${
            t.amount < 0 ? "text-red-600" : "text-green-600"
          }`}
        >
          {formatAmount(t.amount, t.currency)}
        </span>
      ),
      serverSortKey: "amount",
      className: "text-right",
    },
    {
      header: "Kategoria",
      accessor: (t) =>
        t.category_name ? (
          <span className="text-gray-700 text-xs truncate max-w-[160px] block">
            {t.category_name}
          </span>
        ) : (
          <span className="text-gray-400 italic text-xs">Nie przypisano</span>
        ),
      serverSortKey: "category_name",
    },
    {
      header: "Źródło",
      accessor: (t) => <SourceBadge source={t.source} />,
    },
    {
      header: "Tagi",
      accessor: (t) =>
        t.tags && t.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {t.tags.map((tag) => (
              <span
                key={tag}
                className="inline-block bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full text-xs px-2 py-0.5 font-medium"
              >
                {tag}
              </span>
            ))}
          </div>
        ) : null,
    },
    {
      header: "Status",
      accessor: (t) => <StatusBadge status={t.status} />,
      serverSortKey: "status",
    },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold text-gray-800">
          Transakcje gotówkowe
        </h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-md bg-[#635bff] text-white
                     text-sm font-medium hover:bg-[#4b44cc] transition-colors"
        >
          <Plus className="h-4 w-4" />
          Dodaj transakcję
        </button>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => {
              setStatusFilter(f);
              setPage(1);
            }}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              statusFilter === f
                ? "border-[#635bff] text-[#635bff]"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {f === "all"
              ? "Wszystkie"
              : f === "to_confirm"
              ? "Do potwierdzenia"
              : "Potwierdzone"}
            <span className="ml-1.5 text-xs bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5">
              {f === "all" ? totalAll : (statusCounts[f] ?? 0)}
            </span>
          </button>
        ))}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="p-8 text-center text-gray-400 text-sm">Ładowanie…</div>
      ) : (
        <DataTable
          columns={columns}
          rows={transactions}
          emptyMessage="Brak transakcji gotówkowych. Kliknij „Dodaj transakcję" aby dodać pierwszą."
          renderExpandedRow={(tx) => (
            <ExpandedRowContent tx={tx} allTags={allTags} />
          )}
          className="flex-1 min-h-0"
          pagination={{
            page,
            pageSize: PAGE_SIZE,
            total,
            onPageChange: setPage,
            sortBy,
            sortDir,
            onSortChange: (key, dir) => {
              setSortBy(key);
              setSortDir(dir);
              setPage(1);
            },
          }}
        />
      )}

      {showAddModal && (
        <AddTransactionModal
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
            queryClient.invalidateQueries({ queryKey: ["cash-transactions-counts"] });
          }}
        />
      )}
    </div>
  );
}
