"use client";

import { useState } from "react";
import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import {
  listCashTransactions,
  createCashTransaction,
  saveCashTransactionCategory,
  deleteCashTransaction,
  updateCashTransaction,
  getCashReceiptCandidates,
  linkCashToReceipt,
  unlinkCashTransaction,
  updateCashTransactionTags,
  getAllTags,
  listVendors,
  getCashTransaction,
} from "@/lib/api";
import { isoToDisplay } from "@/lib/utils";
import {
  CashTransactionListItem,
  CashTransactionCreate,
  CashTransactionDetail,
  ReceiptCandidateItem,
  VendorItem,
} from "@/lib/types";
import { CategoryDropdown } from "@/components/CategoryDropdown";
import { VendorDropdown } from "@/components/VendorDropdown";
import TagsEditor from "@/components/TagsEditor";
import { DataTable, Column } from "@/components/DataTable";
import { SettlementOperationsSection } from "@/components/SettlementOperationsSection";
import Link from "next/link";
import { Plus, Link2, ArrowRight } from "lucide-react";
import {
  SourceBadge,
  MatchBadge,
  CountBadge,
  Pill,
  PageHeader,
  SectionLabel,
  NavLink,
  Button,
  Amount,
  Modal,
  ThreeDotsMenu,
  ConfirmDeleteModal,
  DateInput,
  AmountInput,
} from "@/components/ui";
import {
  QueryState,
  QueryErrorNotice,
  MutationErrorNotice,
} from "@/components/QueryState";

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
  const [amount, setAmount] = useState<number | null>(null);
  const [isExpense, setIsExpense] = useState(true);
  const [description, setDescription] = useState("");
  const [categoryId, setCategoryId] = useState<number | undefined>();
  const [vendorName, setVendorName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const vendorsQuery = useQuery<VendorItem[]>({
    queryKey: ["vendors"],
    queryFn: listVendors,
  });
  const vendors = vendorsQuery.data ?? [];

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
    if (amount === null || amount <= 0) {
      setError("Podaj prawidłową kwotę (liczbę dodatnią).");
      return;
    }
    const signedAmount = isExpense ? -amount : amount;
    const matchedVendor = vendors.find(
      (v) => v.name.toLowerCase() === vendorName.trim().toLowerCase()
    );
    createMutation.mutate({
      booking_date: date,
      amount: signedAmount,
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
        <QueryErrorNotice
          query={vendorsQuery}
          errorTitle="Nie udało się pobrać listy dostawców (dopasowanie przy zapisie)."
        />
        <MutationErrorNotice mutation={createMutation} />
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Date */}
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">
              Data
            </label>
            <DateInput
              value={date}
              onChange={setDate}
              inputSize="md"
              className="w-full"
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
              <AmountInput
                value={amount}
                onChange={setAmount}
                placeholder="0,00"
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
  tagsQuery: UseQueryResult<string[], Error>;
};

function ExpandedRowContent({ tx, tagsQuery }: ExpandedRowProps) {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<number | undefined>(
    tx.category_id ?? undefined
  );
  const [showCandidates, setShowCandidates] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);

  // Edit state
  const [editMode, setEditMode] = useState(false);
  const [editDate, setEditDate] = useState(tx.booking_date);
  const [editAmount, setEditAmount] = useState<number | null>(Math.abs(tx.amount));
  const [editIsExpense, setEditIsExpense] = useState(tx.amount <= 0);
  const [editDescription, setEditDescription] = useState(tx.description ?? "");
  const [editVendorName, setEditVendorName] = useState(tx.vendor_name ?? "");

  const vendorsQuery = useQuery<VendorItem[]>({
    queryKey: ["vendors"],
    queryFn: listVendors,
    enabled: editMode,
  });
  const vendors = vendorsQuery.data ?? [];

  const detailQuery = useQuery<CashTransactionDetail>({
    queryKey: ["cash-transaction", tx.id],
    queryFn: () => getCashTransaction(tx.id),
  });
  const detail = detailQuery.data;

  const candidatesQuery = useQuery<ReceiptCandidateItem[]>({
    queryKey: ["cash-tx-receipt-candidates", tx.id],
    queryFn: () => getCashReceiptCandidates(tx.id),
    enabled: showCandidates,
  });

  const saveCategoryMutation = useMutation({
    mutationFn: (categoryId: number | null) => saveCashTransactionCategory(tx.id, categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["cash-transaction", tx.id] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteCashTransaction(tx.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: () => {
      const amount = editIsExpense ? -(editAmount ?? 0) : (editAmount ?? 0);
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
    <>
    <QueryErrorNotice
      query={detailQuery}
      errorTitle="Nie udało się pobrać szczegółów transakcji."
    />
    {editMode && (
      <QueryErrorNotice
        query={vendorsQuery}
        errorTitle="Nie udało się pobrać listy dostawców."
      />
    )}
    <MutationErrorNotice mutation={saveCategoryMutation} />
    <MutationErrorNotice mutation={deleteMutation} />
    <MutationErrorNotice mutation={updateMutation} />
    <MutationErrorNotice mutation={linkMutation} />
    <MutationErrorNotice mutation={unlinkMutation} />
    <MutationErrorNotice mutation={tagsMutation} />
    <div className="flex gap-8">
      {/* Left: details / edit form */}
      <div className="flex-1 space-y-3">
        {editMode ? (
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="block text-xs font-medium text-gray-500 mb-1">Data</label>
                <DateInput
                  value={editDate}
                  onChange={setEditDate}
                  inputSize="sm"
                  className="w-full"
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
                  <AmountInput
                    value={editAmount}
                    onChange={setEditAmount}
                    placeholder="0,00"
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
          <QueryState
            query={tagsQuery}
            errorTitle="Nie udało się pobrać listy tagów."
            loadingFallback={
              <p className="text-xs text-gray-400">Ładowanie tagów…</p>
            }
          >
            {(allTags) => (
              <TagsEditor
                tags={tx.tags ?? []}
                allTags={allTags}
                onChange={(tags) => tagsMutation.mutate(tags)}
              />
            )}
          </QueryState>
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

        {/* Save category */}
        {!receiptLink && (
          <div className="flex gap-2">
            <Button
              variant="primary"
              size="sm"
              disabled={!selectedCategory || saveCategoryMutation.isPending}
              onClick={() => saveCategoryMutation.mutate(selectedCategory ?? null)}
              className="flex-1"
            >
              {saveCategoryMutation.isPending ? "Zapisywanie…" : "Zapisz kategorię"}
            </Button>
          </div>
        )}

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
                  {receiptLink.vendor_name} · {isoToDisplay(receiptLink.date)} ·{" "}
                  {receiptLink.total.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN
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
                <QueryState
                  query={candidatesQuery}
                  errorTitle="Nie udało się pobrać propozycji paragonów."
                  loadingFallback={
                    <p className="text-xs text-gray-400">Szukanie…</p>
                  }
                >
                  {(candidates) => (
                <div className="space-y-1.5">
                  {candidates.length === 0 ? (
                    <p className="text-xs text-gray-400">
                      Nie znaleziono pasujących paragonów.
                    </p>
                  ) : (
                    candidates.map((c) => (
                    <div
                      key={c.receipt_transaction_id}
                      className="flex items-center justify-between rounded-md bg-gray-50 border border-gray-200 px-3 py-2 text-xs"
                    >
                      <div>
                        <span className="font-medium text-gray-700">
                          {c.vendor_name}
                        </span>
                        <span className="text-gray-400 ml-2">
                          {isoToDisplay(c.date)} · {c.total.toLocaleString("pl-PL", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} PLN
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
                    ))
                  )}
                  <button
                    type="button"
                    onClick={() => setShowCandidates(false)}
                    className="text-xs text-gray-400 hover:text-gray-600"
                  >
                    Ukryj
                  </button>
                </div>
                  )}
                </QueryState>
              )}
            </div>
          )}
        </div>
      </div>
    </div>

    <div
      className="mt-4 pt-4 border-t border-gray-200"
      onClick={(e) => e.stopPropagation()}
    >
      <SettlementOperationsSection sourceType="cash" transactionId={tx.id} />
    </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function CashTransactionsPage() {
  const queryClient = useQueryClient();
  const PAGE_SIZE = 50;
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("booking_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [showAddModal, setShowAddModal] = useState(false);

  const listQuery = useQuery({
    queryKey: ["cash-transactions", page, sortBy, sortDir],
    queryFn: () =>
      listCashTransactions({
        page,
        limit: PAGE_SIZE,
        sort_by: sortBy,
        sort_dir: sortDir,
      }),
    staleTime: 30_000,
  });

  const tagsQuery = useQuery({
    queryKey: ["tags"],
    queryFn: getAllTags,
    staleTime: 60_000,
  });

  const columns: Column<CashTransactionListItem>[] = [
    {
      header: "Data",
      accessor: (t) => (
        <Link
          href={`/cash-transactions/${t.id}`}
          onClick={(e) => e.stopPropagation()}
          className="font-mono text-xs text-violet-600 hover:underline"
        >
          {isoToDisplay(t.booking_date)}
        </Link>
      ),
      serverSortKey: "booking_date",
      className: "whitespace-nowrap",
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
      header: "",
      accessor: (t) =>
        t.settlement_group_id != null ? (
          <Link
            href={`/settlement-groups/${t.settlement_group_id}`}
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 max-w-[10rem] p-1 rounded hover:bg-violet-50 text-violet-600 min-w-0"
            title={
              t.settlement_group_title?.trim()
                ? t.settlement_group_title
                : "Powiązane operacje"
            }
          >
            <Link2 className="h-4 w-4 shrink-0" />
            {t.settlement_group_title?.trim() ? (
              <span className="truncate text-xs font-medium text-violet-800">
                {t.settlement_group_title}
              </span>
            ) : null}
          </Link>
        ) : null,
      className: "w-36",
    },
    {
      header: "",
      accessor: (t) => (
        <Link
          href={`/cash-transactions/${t.id}`}
          onClick={(e) => e.stopPropagation()}
          className="flex items-center justify-center p-1 rounded hover:bg-gray-100 text-gray-400 hover:text-accent transition-colors"
          title="Otwórz szczegóły"
        >
          <ArrowRight className="h-4 w-4" />
        </Link>
      ),
      className: "w-8 text-center",
    },
  ];

  return (
    <div className="h-full flex flex-col gap-4">
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

      {/* Table */}
      <QueryState
        query={listQuery}
        errorTitle="Nie udało się pobrać transakcji gotówkowych."
        loadingFallback={
          <div className="p-8 text-center text-gray-400 text-sm">Ładowanie…</div>
        }
      >
        {(data) => (
          <DataTable
            columns={columns}
            rows={data.items}
            emptyMessage={
              "Brak transakcji gotówkowych. Kliknij „Dodaj transakcję” aby dodać pierwszą."
            }
            renderExpandedRow={(tx) => (
              <ExpandedRowContent tx={tx} tagsQuery={tagsQuery} />
            )}
            className="flex-1 min-h-0"
            pagination={{
              page,
              pageSize: PAGE_SIZE,
              total: data.total,
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
      </QueryState>

      {showAddModal && (
        <AddTransactionModal
          onClose={() => setShowAddModal(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ["cash-transactions"] });
          }}
        />
      )}
    </div>
  );
}
