"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Search,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { SOURCE_CONFIG } from "@/lib/sourceConfig";
import {
  listUnifiedTransactions,
  saveBankTransactionCategory,
  saveCashTransactionCategory,
  updateBankTransactionTags,
  updateCashTransactionTags,
  updateReceiptTags,
  getAllTags,
  getReceiptCandidates,
  getCashReceiptCandidates,
  linkBankToReceipt,
  linkCashToReceipt,
  unlinkBankTransaction,
  unlinkCashTransaction,
} from "@/lib/api";
import { UnifiedTransaction, ReceiptCandidateItem } from "@/lib/types";
import { isoToDisplay } from "@/lib/utils";
import { DataTable, Column } from "@/components/DataTable";
import { CategoryDropdown } from "@/components/CategoryDropdown";
import TagsEditor from "@/components/TagsEditor";
import {
  StatusBadge,
  SourceBadge,
  CountBadge,
  PageHeader,
  FilterTabs,
  Input,
  SectionLabel,
  NavLink,
  Pill,
  Amount,
  DateInput,
  MatchBadge,
  Button,
} from "@/components/ui";
import Link from "next/link";

// ─── Helpers ───────────────────────────────────────────────────────
function dateRangeFor(preset: string): { date_from: string; date_to: string } {
  const today = new Date();
  const to = today.toISOString().slice(0, 10);
  const from = new Date(today);
  if (preset === "1m")  from.setMonth(today.getMonth() - 1);
  if (preset === "3m")  from.setMonth(today.getMonth() - 3);
  if (preset === "6m")  from.setMonth(today.getMonth() - 6);
  if (preset === "12m") from.setFullYear(today.getFullYear() - 1);
  if (preset === "ytd") from.setMonth(0, 1);
  return { date_from: from.toISOString().slice(0, 10), date_to: to };
}

// ─── Expanded row ───────────────────────────────────────────────────
function ExpandedRow({
  row,
  allTags,
  onCategoryConfirm,
  onTagsChange,
}: {
  row: UnifiedTransaction;
  allTags: string[];
  onCategoryConfirm: (row: UnifiedTransaction, categoryId: number) => void;
  onTagsChange: (row: UnifiedTransaction, tags: string[]) => void;
}) {
  const queryClient = useQueryClient();
  const [showCandidates, setShowCandidates] = useState(false);

  const isLinkable = row.source_type === "bank" || row.source_type === "cash";

  const { data: detail } = useQuery({
    queryKey: ["tx-detail", row.source_type, row.id],
    queryFn: () =>
      row.source_type === "bank"
        ? fetch(`/api/bank-transactions/${row.id}`).then((r) => r.json())
        : fetch(`/api/cash-transactions/${row.id}`).then((r) => r.json()),
    enabled: isLinkable,
  });

  const { data: candidates = [], isFetching: candidatesLoading } = useQuery<ReceiptCandidateItem[]>({
    queryKey: ["tx-receipt-candidates", row.source_type, row.id],
    queryFn: () =>
      row.source_type === "bank"
        ? getReceiptCandidates(row.id)
        : getCashReceiptCandidates(row.id),
    enabled: showCandidates && isLinkable,
  });

  const linkMutation = useMutation<unknown, Error, number>({
    mutationFn: (receiptTxId: number) =>
      row.source_type === "bank"
        ? linkBankToReceipt(row.id, receiptTxId)
        : linkCashToReceipt(row.id, receiptTxId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["tx-detail", row.source_type, row.id] });
      queryClient.invalidateQueries({ queryKey: ["tx-receipt-candidates", row.source_type, row.id] });
      setShowCandidates(false);
    },
  });

  const unlinkMutation = useMutation<unknown, Error, void>({
    mutationFn: () =>
      row.source_type === "bank"
        ? unlinkBankTransaction(row.id)
        : unlinkCashTransaction(row.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["tx-detail", row.source_type, row.id] });
    },
  });

  const receiptLink = detail?.receipt_link ?? null;

  const detailHref =
    row.source_type === "bank"
      ? `/bank-transactions/${row.id}`
      : row.source_type === "cash"
      ? `/cash-transactions`
      : `/receipts/${row.id}`;

  return (
    <div>
      <div className="flex gap-8">
        {/* ── Details col ─────────────────────────────────────────── */}
        <div className="flex-1 space-y-1.5">
          <SectionLabel>Szczegóły</SectionLabel>
          <div className="flex flex-col gap-1 text-sm text-gray-700">
            <span>
              <span className="font-medium text-gray-500">Źródło: </span>
              <SourceBadge source={row.source_type} showLabel />
            </span>
            {(row.vendor_name || row.description) && (
              <span>
                <span className="font-medium text-gray-500">Sklep: </span>
                {row.vendor_name ?? row.description}
              </span>
            )}
            {row.vendor_name && row.description && row.description !== row.vendor_name && (
              <span>
                <span className="font-medium text-gray-500">Opis: </span>
                {row.description}
              </span>
            )}
            {row.has_receipt && row.receipt_scan_id != null && (
              <NavLink
                href={`/receipts/${row.receipt_scan_id}`}
                label="Zobacz paragon"
                variant="forward"
              />
            )}
            <NavLink
              href={detailHref}
              label="Otwórz szczegóły"
              variant="forward"
              className="mt-1"
            />
          </div>
        </div>

        {/* ── Category col ────────────────────────────────────────── */}
        <div className="w-96 space-y-1.5">
          <SectionLabel>Kategoria</SectionLabel>
          {row.source_type === "receipt" ? (
            <p className="text-xs text-gray-400">
              Kategorie przypisane per produkt w szczegółach paragonu.
            </p>
          ) : row.has_receipt && (row.receipt_categories?.length ?? 0) > 0 ? (
            <div className="space-y-1.5">
              <div className="flex flex-col gap-1">
                {row.receipt_categories!.map((cat, idx) => (
                  <Pill
                    key={cat.id}
                    variant={idx === 0 ? "category-primary" : "category-secondary"}
                    size="sm"
                  >
                    {cat.name}
                    <span className="ml-1 text-[10px] text-gray-400">({cat.product_count})</span>
                  </Pill>
                ))}
              </div>
              {row.receipt_scan_id && (
                <NavLink
                  href={`/receipts/${row.receipt_scan_id}`}
                  label="Zarządzaj kategoriami w paragonie"
                  variant="forward"
                />
              )}
            </div>
          ) : row.has_receipt && row.receipt_category_name ? (
            <div className="space-y-1.5">
              <span className="text-xs text-gray-700">{row.receipt_category_name}</span>
              {row.receipt_scan_id && (
                <NavLink
                  href={`/receipts/${row.receipt_scan_id}`}
                  label="Zarządzaj kategoriami w paragonie"
                  variant="forward"
                />
              )}
            </div>
          ) : (
            <div className="max-w-xs">
              <CategoryDropdown
                value={row.category_id ?? undefined}
                onChange={(categoryId) => onCategoryConfirm(row, categoryId)}
              />
            </div>
          )}
        </div>
      </div>

      {/* ── Tags — separate border section ──────────────────────── */}
      <div className="mt-4 pt-4 border-t border-gray-200 space-y-1.5">
        <SectionLabel>Tagi</SectionLabel>
        <TagsEditor
          tags={row.tags ?? []}
          allTags={allTags}
          onChange={(tags) => onTagsChange(row, tags)}
        />
      </div>

      {/* ── Receipt linking — only for bank/cash ────────────────── */}
      {isLinkable && (
        <div className="mt-4 pt-4 border-t border-gray-200 space-y-1.5">
          <SectionLabel>Powiązany paragon</SectionLabel>

          {receiptLink ? (
            <div className="flex items-center justify-between gap-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2">
              <Link
                href={`/receipts/${receiptLink.scan_id}`}
                className="text-xs space-y-0.5 hover:underline min-w-0"
                onClick={(e) => e.stopPropagation()}
              >
                <p className="font-medium text-accent">{receiptLink.vendor_name}</p>
                <p className="text-gray-500">
                  {isoToDisplay(receiptLink.date)} · {receiptLink.total.toFixed(2)} PLN
                </p>
                <p className="text-gray-400 font-mono">{receiptLink.scan_filename}</p>
              </Link>
              <Button
                variant="danger"
                size="sm"
                disabled={unlinkMutation.isPending}
                onClick={() => unlinkMutation.mutate()}
                className="shrink-0"
              >
                {unlinkMutation.isPending ? "…" : "Odepnij"}
              </Button>
            </div>
          ) : showCandidates ? (
            candidatesLoading ? (
              <p className="text-xs text-gray-400 animate-pulse">Szukanie…</p>
            ) : candidates.length === 0 ? (
              <p className="text-xs text-gray-400 italic">Nie znaleziono pasujących paragonów.</p>
            ) : (
              <div className="space-y-1.5">
                {candidates.map((c) => (
                  <div
                    key={c.receipt_transaction_id}
                    className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2"
                  >
                    <div className="text-xs space-y-0.5 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium text-gray-800 truncate">{c.vendor_name}</p>
                        <MatchBadge score={c.match_score} />
                      </div>
                      <p className="text-gray-500">
                        {c.date} · {c.total.toFixed(2)} PLN
                      </p>
                      <p className="text-gray-400 font-mono text-[10px] truncate">{c.scan_filename}</p>
                    </div>
                    <Button
                      variant="primary"
                      size="sm"
                      disabled={linkMutation.isPending}
                      onClick={() => linkMutation.mutate(c.receipt_transaction_id)}
                      className="shrink-0"
                    >
                      {linkMutation.isPending ? "…" : "Powiąż"}
                    </Button>
                  </div>
                ))}
              </div>
            )
          ) : (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowCandidates(true)}
            >
              Znajdź pasujące paragony
            </Button>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Main page ──────────────────────────────────────────────────────

const DATE_PRESETS = [
  { label: "1m", value: "1m" },
  { label: "3m", value: "3m" },
  { label: "6m", value: "6m" },
  { label: "12m", value: "12m" },
  { label: "YTD", value: "ytd" },
];

type Filters = {
  source_type: string;
  status: string;
  direction: string;
  search: string;
  date_from: string;
  date_to: string;
  amount_min: string;
  amount_max: string;
  tag: string;
};

const defaultFilters: Filters = {
  source_type: "",
  status: "",
  direction: "",
  search: "",
  date_from: "",
  date_to: "",
  amount_min: "",
  amount_max: "",
  tag: "",
};

export default function TransactionsPage() {
  const queryClient = useQueryClient();

  // ── Pagination & sort ──────────────────────────────────────────
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState("date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  // ── Filters ───────────────────────────────────────────────────
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const setFilter = useCallback(
    (key: keyof Filters, value: string) =>
      setFilters((f) => ({ ...f, [key]: value })),
    []
  );

  // ── Date preset ───────────────────────────────────────────────
  const [activePreset, setActivePreset] = useState("1m");
  function applyPreset(preset: string) {
    setActivePreset(preset);
    const range = dateRangeFor(preset);
    setFilters((f) => ({
      ...f,
      date_from: range.date_from,
      date_to: range.date_to,
    }));
    setPage(1);
  }

  // ── Query keys ────────────────────────────────────────────────
  const listKey = [
    "transactions",
    page,
    sortBy,
    sortDir,
    filters.source_type,
    filters.status,
    filters.direction,
    filters.date_from,
    filters.date_to,
    filters.search,
    filters.amount_min,
    filters.amount_max,
    filters.tag,
  ];

  // ── Data fetching ─────────────────────────────────────────────
  const { data: listData, isFetching } = useQuery({
    queryKey: listKey,
    queryFn: () =>
      listUnifiedTransactions({
        page,
        limit: 50,
        sort_by: sortBy,
        sort_dir: sortDir,
        source_type: filters.source_type || undefined,
        status: filters.status || undefined,
        direction: filters.direction || undefined,
        date_from: filters.date_from || undefined,
        date_to: filters.date_to || undefined,
        search: filters.search || undefined,
        amount_min: filters.amount_min ? parseFloat(filters.amount_min) : undefined,
        amount_max: filters.amount_max ? parseFloat(filters.amount_max) : undefined,
        tag: filters.tag || undefined,
      }),
    staleTime: 30_000,
    placeholderData: (prev) => prev,
  });

  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: getAllTags,
    staleTime: 120_000,
  });

  // ── Mutations ─────────────────────────────────────────────────
  const categoryMutation = useMutation<unknown, Error, { row: UnifiedTransaction; categoryId: number }>({
    mutationFn: ({
      row,
      categoryId,
    }: {
      row: UnifiedTransaction;
      categoryId: number;
    }) => {
      if (row.source_type === "bank")
        return saveBankTransactionCategory(row.id, categoryId);
      return saveCashTransactionCategory(row.id, categoryId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
    },
  });

  const tagsMutation = useMutation<unknown, Error, { row: UnifiedTransaction; tags: string[] }>({
    mutationFn: ({
      row,
      tags,
    }: {
      row: UnifiedTransaction;
      tags: string[];
    }) => {
      if (row.source_type === "bank")
        return updateBankTransactionTags(row.id, tags);
      if (row.source_type === "cash")
        return updateCashTransactionTags(row.id, tags);
      return updateReceiptTags(row.id, tags) as Promise<unknown>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  // ── Sort handler ──────────────────────────────────────────────
  function handleSortChange(key: string, dir: "asc" | "desc") {
    setSortBy(key);
    setSortDir(dir);
    setPage(1);
  }

  // ── Clear filters ─────────────────────────────────────────────
  function clearFilters() {
    setFilters(defaultFilters);
    setPage(1);
  }

  const hasActiveFilters =
    !!filters.source_type ||
    !!filters.status ||
    !!filters.direction ||
    !!filters.search ||
    !!filters.date_from ||
    !!filters.date_to ||
    !!filters.amount_min ||
    !!filters.amount_max ||
    !!filters.tag;

  // ── Table columns ─────────────────────────────────────────────
  const columns: Column<UnifiedTransaction>[] = [
    {
      header: "Data",
      serverSortKey: "date",
      accessor: (r) => (
        <span className="font-mono text-xs text-gray-600">{isoToDisplay(r.date)}</span>
      ),
      className: "w-28",
    },
    {
      header: "Sklep",
      serverSortKey: "description",
      className: "w-64",
      accessor: (r) => (
        <div className="flex items-center gap-2 min-w-0">
          <SourceBadge source={r.source_type} />
          <span className="truncate text-gray-800 font-medium">
            {r.vendor_name ?? r.description}
          </span>
        </div>
      ),
    },
    {
      header: "Kwota",
      serverSortKey: "amount",
      className: "text-right w-32 whitespace-nowrap",
      accessor: (r) => (
        <Amount value={r.amount} currency={r.currency} />
      ),
    },
    {
      header: "Kategoria",
      serverSortKey: "category_name",
      className: "w-52",
      accessor: (r) => {
        if (r.has_receipt && r.receipt_category_name) {
          return (
            <div className="flex items-center gap-1 flex-wrap">
              <span className="text-xs text-gray-700">
                {r.receipt_category_name}
              </span>
              {(r.receipt_category_count ?? 1) > 1 && (
                <CountBadge count={r.receipt_category_count! - 1} className="shrink-0" />
              )}
            </div>
          );
        }
        return r.category_name ? (
          <span className="text-xs text-gray-700">
            {r.category_name}
          </span>
        ) : (
          <span className="text-gray-300 text-xs">—</span>
        );
      },
    },
    {
      header: "Tagi",
      className: "w-40",
      accessor: (r) =>
        (r.tags ?? []).length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {r.tags!.map((t) => (
              <Pill key={t} variant="tag" size="sm">{t}</Pill>
            ))}
          </div>
        ) : (
          <span className="text-gray-300 text-xs">—</span>
        ),
    },
    {
      header: "Status",
      serverSortKey: "status",
      accessor: (r) => (
        <div className="flex items-center gap-1.5">
          {r.source_type === "receipt" && <StatusBadge status={r.status} />}
          {r.has_receipt && (() => {
            const { icon: Icon, style } = SOURCE_CONFIG.receipt;
            return (
              <span title="Powiązany paragon" className={`inline-flex rounded-full p-0.5 ${style}`}>
                <Icon size={12} />
              </span>
            );
          })()}
        </div>
      ),
      className: "w-40",
    },
  ];

  // ── Source type tab labels ─────────────────────────────────────
  const sourceTabs = [
    { label: "Wszystkie", value: "" },
    { label: "Bankowe", value: "bank" },
    { label: "Gotówkowe", value: "cash" },
    { label: "Paragony", value: "receipt" },
  ];

  const statusTabs = [
    { label: "Wszystkie statusy", value: "" },
    { label: "Do potwierdzenia", value: "to_confirm" },
    { label: "Gotowe", value: "done" },
  ];

  const directionTabs = [
    { label: "Wszystkie", value: "" },
    { label: "Wydatki", value: "expense" },
    { label: "Przychody", value: "income" },
  ];

  const items = listData?.items ?? [];
  const total = listData?.total ?? 0;

  return (
    <div className="flex flex-col h-full gap-6">
      {/* ── Page header ─────────────────────────────────────────── */}
      <PageHeader
        title="Transakcje"
        subtitle="Wszystkie transakcje"
        actions={
          /* Date preset pills */
          <div className="flex items-center gap-1 bg-gray-100 rounded-lg p-1 flex-wrap">
            {DATE_PRESETS.map((p) => (
              <button
                key={p.value}
                onClick={() => applyPreset(p.value)}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${
                  activePreset === p.value
                    ? "bg-white shadow text-accent"
                    : "text-gray-500 hover:text-gray-800"
                }`}
              >
                {p.label}
              </button>
            ))}
            <div className="w-px h-4 bg-gray-300 mx-1" />
            <DateInput
              value={filters.date_from}
              onChange={(iso) => {
                setFilter("date_from", iso);
                setActivePreset("custom");
                setPage(1);
              }}
              inputSize="xs"
              className="w-32"
            />
            <span className="text-gray-400 text-xs">–</span>
            <DateInput
              value={filters.date_to}
              onChange={(iso) => {
                setFilter("date_to", iso);
                setActivePreset("custom");
                setPage(1);
              }}
              inputSize="xs"
              className="w-32"
            />
          </div>
        }
      />

      {/* ── Filters ─────────────────────────────────────────────── */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 flex-wrap">
          <FilterTabs
            tabs={sourceTabs}
            value={filters.source_type}
            onChange={(v) => {
              setFilter("source_type", v);
              if (v !== "receipt") setFilter("status", "");
              setPage(1);
            }}
          />
          <FilterTabs
            tabs={directionTabs}
            value={filters.direction}
            onChange={(v) => { setFilter("direction", v); setPage(1); }}
          />

          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-400" />
            <Input
              inputSize="sm"
              type="text"
              value={filters.search}
              onChange={(e) => { setFilter("search", e.target.value); setPage(1); }}
              placeholder="Szukaj opisu lub sklepu…"
              className="pl-8 w-56"
            />
          </div>

          <button
            onClick={() => setShowAdvanced((v) => !v)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs border rounded-lg transition-colors ${
              showAdvanced
                ? "border-accent text-accent bg-accent/5"
                : "border-gray-200 text-gray-600 bg-white hover:bg-gray-50"
            }`}
          >
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Filtry
          </button>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
            >
              <X className="h-3.5 w-3.5" /> Wyczyść
            </button>
          )}

          <span className="ml-auto text-xs text-gray-400">
            {isFetching ? "Ładowanie…" : `${total.toLocaleString("pl-PL")} transakcji`}
          </span>
        </div>

        {/* Second row: status filter — always rendered to prevent table shift */}
        <div
          className={`flex items-center gap-2 h-9 transition-opacity duration-150 ${
            filters.source_type === "receipt"
              ? "opacity-100 pointer-events-auto"
              : "opacity-0 pointer-events-none"
          }`}
        >
          <FilterTabs
            tabs={statusTabs}
            value={filters.status}
            onChange={(v) => { setFilter("status", v); setPage(1); }}
          />
        </div>

        {/* Advanced filter panel */}
        {showAdvanced && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 p-4 border border-gray-200 rounded-xl bg-white">
            <div>
              <SectionLabel as="div" className="mb-1">Tag</SectionLabel>
              <Input
                inputSize="sm"
                list="unified-tags"
                value={filters.tag}
                onChange={(e) => { setFilter("tag", e.target.value); setPage(1); }}
                placeholder="Filtruj po tagu…"
                className="w-full"
              />
              <datalist id="unified-tags">
                {allTags.map((t) => (
                  <option key={t} value={t} />
                ))}
              </datalist>
            </div>
            <div>
              <SectionLabel as="div" className="mb-1">Kwota min (abs)</SectionLabel>
              <Input
                inputSize="sm"
                type="number"
                value={filters.amount_min}
                onChange={(e) => { setFilter("amount_min", e.target.value); setPage(1); }}
                placeholder="0.00"
                className="w-full"
              />
            </div>
            <div>
              <SectionLabel as="div" className="mb-1">Kwota max (abs)</SectionLabel>
              <Input
                inputSize="sm"
                type="number"
                value={filters.amount_max}
                onChange={(e) => { setFilter("amount_max", e.target.value); setPage(1); }}
                placeholder="9999.99"
                className="w-full"
              />
            </div>
            <div className="flex items-end">
              <button
                onClick={clearFilters}
                className="text-xs text-gray-500 hover:text-red-600 flex items-center gap-1"
              >
                <X className="h-3.5 w-3.5" /> Resetuj filtry
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Table ───────────────────────────────────────────────── */}
      <DataTable<UnifiedTransaction>
        columns={columns}
        rows={items}
        emptyMessage="Brak transakcji dla wybranych filtrów."
        renderExpandedRow={(row) => (
          <ExpandedRow
            row={row}
            allTags={allTags}
            onCategoryConfirm={(r, catId) =>
              categoryMutation.mutate({ row: r, categoryId: catId })
            }
            onTagsChange={(r, tags) => tagsMutation.mutate({ row: r, tags })}
          />
        )}
        pagination={{
          page,
          pageSize: 50,
          total,
          onPageChange: setPage,
          sortBy,
          sortDir,
          onSortChange: handleSortChange,
        }}
      />
    </div>
  );
}

