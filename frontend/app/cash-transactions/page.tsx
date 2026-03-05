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
import TagsEditor from "@/components/TagsEditor";
import { DataTable, Column } from "@/components/DataTable";
import Link from "next/link";
import { Plus } from "lucide-react";
import {
  StatusBadge,
  SourceBadge,
  MatchBadge,
  CountBadge,
  Pill,
  PageHeader,
  FilterTabs,
  SectionLabel,
  NavLink,
  Button,
  Amount,
  Modal,
  ThreeDotsMenu,
  ConfirmDeleteModal,
} from "@/components/ui";

const STATUS_FILTERS = ["all", "to_confirm", "done"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

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
    <Modal open onClose={onClose} maxWidth="md">
      <div className="p-6">
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
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus-ring"
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
                className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus-ring"
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
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus-ring resize-none"
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
            <Button variant="secondary" size="md" type="button" onClick={onClose} className="flex-1">
              Anuluj
            </Button>
            <Button variant="primary" size="md" type="submit" disabled={createMutation.isPending} className="flex-1">
              {createMutation.isPending ? "Zapisywanie…" : "Dodaj"}
            </Button>
          </div>
        </form>
      </div>
    </Modal>
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
  const [showDeleteModal, setShowDeleteModal] = useState(false);

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
    mutationFn: (categoryId: number | null) => confirmCashTransaction(tx.id, categoryId),
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
              <Button
                variant="primary"
                size="sm"
                onClick={() => updateMutation.mutate()}
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending ? "Zapisywanie…" : "Zapisz"}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setEditMode(false)}
              >
                Anuluj
              </Button>
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
                  className="text-accent hover:underline"
                >
                  #{detail.receipt_scan_id}
                </Link>
              </div>
            )}
            <button
              onClick={() => setEditMode(true)}
              className="mt-1 text-xs text-accent hover:underline"
            >
              Edytuj
            </button>
          </div>
        )}

        {/* Tags */}
        <div>
          <SectionLabel className="mb-1">Tagi</SectionLabel>
          <TagsEditor
            tags={tx.tags ?? []}
            allTags={allTags}
            onChange={(tags) => tagsMutation.mutate(tags)}
          />
        </div>
      </div>

      {/* Right: category + confirm/reopen + receipt linking + delete */}
      <div className="w-96 space-y-4">
        {/* ConfirmDeleteModal */}
        <ConfirmDeleteModal
          open={showDeleteModal}
          onClose={() => setShowDeleteModal(false)}
          onConfirm={() => deleteMutation.mutate()}
          title="Usuń transakcję"
          description="Transakcja zostanie trwale usunięta."
          loading={deleteMutation.isPending}
        />
        {/* Category */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <SectionLabel>Kategoria</SectionLabel>
            <ThreeDotsMenu
              variant="inline"
              items={[
                { label: "Edytuj", onClick: () => setEditMode(true) },
                { separator: true, label: "Usuń transakcję", variant: "danger", onClick: () => setShowDeleteModal(true) },
              ]}
            />
          </div>
          {receiptLink ? (
            /* Receipt-linked: categories derived from receipt items */
            <div className="space-y-2">
              <div className="flex flex-col gap-1">
                {(detail?.receipt_categories ?? []).length > 0 ? (
                  (detail?.receipt_categories ?? []).map((cat: { id: number; name: string; product_count: number }, idx: number) => (
                    <Pill
                      key={cat.id}
                      variant={idx === 0 ? "category-primary" : "category-secondary"}
                      size="sm"
                    >
                      {cat.name}
                      <span className="ml-1 text-[10px] text-gray-400">({cat.product_count})</span>
                    </Pill>
                  ))
                ) : (
                  <span className="text-xs text-gray-400 italic">Paragon bez potwierdzonych kategorii</span>
                )}
              </div>
              <NavLink
                href={`/receipts/${receiptLink.scan_id}`}
                label="Zarządzaj kategoriami w paragonie"
                variant="forward"
                onClick={(e) => e.stopPropagation()}
              />
            </div>
          ) : (
            <CategoryDropdown
              value={selectedCategory}
              onChange={setSelectedCategory}
            />
          )}
        </div>

        {/* Confirm / reopen */}
        <div className="flex gap-2">
          {tx.status === "to_confirm" ? (
            <Button
              variant="primary"
              size="sm"
              disabled={(receiptLink ? false : !selectedCategory) || confirmMutation.isPending}
              onClick={() => confirmMutation.mutate(receiptLink ? null : (selectedCategory ?? null))}
              className="flex-1"
            >
              {confirmMutation.isPending ? "Zapisywanie…" : "Potwierdź"}
            </Button>
          ) : (
            <Button
              variant="secondary"
              size="sm"
              disabled={reopenMutation.isPending}
              onClick={() => reopenMutation.mutate()}
              className="flex-1"
            >
              {reopenMutation.isPending ? "…" : "Cofnij potwierdzenie"}
            </Button>
          )}
        </div>

        {/* Receipt linking */}
        <div>
          <SectionLabel className="mb-1">Paragon</SectionLabel>
          {receiptLink ? (
            <div className="flex items-center justify-between rounded-md bg-green-50 border border-green-200 px-3 py-2 text-xs">
              <div>
                <Link
                  href={`/receipts/${receiptLink.scan_id}`}
                  className="font-medium text-accent hover:underline"
                >
                  {receiptLink.scan_filename}
                </Link>
                <div className="text-gray-500 mt-0.5">
                  {receiptLink.vendor_name} · {receiptLink.date} ·{" "}
                  {receiptLink.total.toFixed(2)} PLN
                </div>
              </div>
              <Button
                variant="danger"
                size="sm"
                onClick={() => unlinkMutation.mutate()}
                disabled={unlinkMutation.isPending}
                className="ml-2 shrink-0"
              >
                Odepnij
              </Button>
            </div>
          ) : (
            <div>
              {!showCandidates ? (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setShowCandidates(true)}
                >
                  Znajdź pasujący paragon
                </Button>
              ) : (
                <div className="space-y-1.5">
                  {candidatesLoading && (
                    <p className="text-xs text-gray-400">Szukanie…</p>
                  )}
                  {!candidatesLoading && candidates.length === 0 && (
                    <p className="text-xs text-gray-400">Nie znaleziono pasujących paragonów.</p>
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
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={() => linkMutation.mutate(c.receipt_transaction_id)}
                        disabled={linkMutation.isPending}
                        className="ml-2 shrink-0"
                      >
                        Powiąż
                      </Button>
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
      accessor: (t) => <Amount value={t.amount} currency={t.currency} />,
      serverSortKey: "amount",
      className: "text-right",
    },
    {
      header: "Kategoria",
      accessor: (t) => {
        if (t.receipt_category_name) {
          return (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-xs text-gray-700">
                {t.receipt_category_name}
              </span>
              {(t.receipt_category_count ?? 1) > 1 && (
                <CountBadge count={t.receipt_category_count! - 1} className="shrink-0" />
              )}
            </div>
          );
        }
        return t.category_name ? (
          <span className="text-gray-700 text-xs truncate max-w-[160px] block">
            {t.category_name}
          </span>
        ) : (
          <span className="text-gray-400 italic text-xs">Nie przypisano</span>
        );
      },
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
              <Pill key={tag} variant="tag" size="sm">{tag}</Pill>
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
      <PageHeader
        title="Transakcje gotówkowe"
        variant="list"
        actions={
          <Button
            variant="primary"
            size="md"
            onClick={() => setShowAddModal(true)}
          >
            <Plus className="h-4 w-4 mr-2" />
            Dodaj transakcję
          </Button>
        }
      />

      {/* Status filter tabs */}
      <div className="flex items-center gap-2 mt-4 mb-4">
        <FilterTabs
          tabs={[
            { value: "all", label: <span>Wszystkie <span className="ml-1 text-xs bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5">{totalAll}</span></span> },
            { value: "to_confirm", label: <span>Do potwierdzenia <span className="ml-1 text-xs bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5">{statusCounts["to_confirm"] ?? 0}</span></span> },
            { value: "done", label: <span>Potwierdzone <span className="ml-1 text-xs bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5">{statusCounts["done"] ?? 0}</span></span> },
          ]}
          value={statusFilter}
          onChange={(v) => { setStatusFilter(v as StatusFilter); setPage(1); }}
        />
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="p-8 text-center text-gray-400 text-sm">Ładowanie…</div>
      ) : (
        <DataTable
          columns={columns}
          rows={transactions}
          emptyMessage={'Brak transakcji gotówkowych. Kliknij \u201eDodaj transakcję\u201d aby dodać pierwszą.'}
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
