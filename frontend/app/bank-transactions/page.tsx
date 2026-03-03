"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  importBankCsv,
  listBankTransactions,
  confirmBankTransaction,
  reopenBankTransaction,
  getReceiptCandidates,
  linkBankToReceipt,
  unlinkBankTransaction,
  getBankTransactionCounts,
  updateBankTransactionTags,
  getAllTags,
} from "@/lib/api";
import {
  BankTransactionListItem,
  BankImportResult,
  ReceiptCandidateItem,
} from "@/lib/types";
import { CategoryDropdown } from "@/components/CategoryDropdown";
import { StatusBadge } from "@/components/StatusBadge";
import TagsEditor from "@/components/TagsEditor";
import { getPusher } from "@/lib/pusher";
import { Upload } from "lucide-react";
import { DataTable, Column } from "@/components/DataTable";
import Link from "next/link";

const STATUS_FILTERS = ["all", "to_confirm", "done"] as const;
type StatusFilter = (typeof STATUS_FILTERS)[number];

function formatAmount(amount: number, currency: string): string {
  return new Intl.NumberFormat("pl-PL", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
  }).format(amount);
}

function CandidateBar({
  name,
  score,
}: {
  name: string;
  score: number;
}) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-48 truncate text-gray-600" title={name}>
        {name}
      </span>
      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
        <div
          className="h-2 rounded-full bg-[#635bff]"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right text-gray-500">{pct}%</span>
    </div>
  );
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

type ExpandedRowProps = {
  tx: BankTransactionListItem;
  allTags?: string[];
};

function ExpandedRowContent({ tx, allTags = [] }: ExpandedRowProps) {
  const queryClient = useQueryClient();
  const [selectedCategory, setSelectedCategory] = useState<number | undefined>(
    tx.category_id ?? undefined
  );
  const [showCandidates, setShowCandidates] = useState(false);

  const { data: detail } = useQuery({
    queryKey: ["bank-transaction", tx.id],
    queryFn: () =>
      fetch(`/api/bank-transactions/${tx.id}`).then((r) => r.json()),
  });

  const { data: candidates = [], isFetching: candidatesLoading } = useQuery<ReceiptCandidateItem[]>({
    queryKey: ["bank-tx-receipt-candidates", tx.id],
    queryFn: () => getReceiptCandidates(tx.id),
    enabled: showCandidates,
  });

  const confirmMutation = useMutation({
    mutationFn: (categoryId: number) => confirmBankTransaction(tx.id, categoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
    },
  });

  const reopenMutation = useMutation({
    mutationFn: () => reopenBankTransaction(tx.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
    },
  });

  const linkMutation = useMutation({
    mutationFn: (receiptTxId: number) => linkBankToReceipt(tx.id, receiptTxId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
      queryClient.invalidateQueries({ queryKey: ["bank-tx-receipt-candidates", tx.id] });
      setShowCandidates(false);
    },
  });

  const unlinkMutation = useMutation({
    mutationFn: () => unlinkBankTransaction(tx.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
    },
  });

  const tagsMutation = useMutation({
    mutationFn: (tags: string[]) => updateBankTransactionTags(tx.id, tags),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
      queryClient.invalidateQueries({ queryKey: ["bank-transaction", tx.id] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const candidates2: Array<{ category_id: number; category_name: string; category_score: number }> =
    detail?.category_candidates ?? [];

  const receiptLink = detail?.receipt_link ?? null;

  // Pre-select the highest-scoring candidate when detail loads and no category is confirmed yet
  useEffect(() => {
    if (tx.category_id != null) return; // already confirmed — don't override
    if (candidates2.length === 0) return;
    if (selectedCategory !== undefined) return; // user already picked something
    const top = [...candidates2].sort((a, b) => b.category_score - a.category_score)[0];
    setSelectedCategory(top.category_id);
  }, [candidates2.length]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
    <div className="flex gap-8">
          {/* Left: details */}
          <div className="flex-1 space-y-1 text-xs text-gray-600">
            {tx.counterparty && (
              <div>
                <span className="font-medium text-gray-700">Kontrahent: </span>
                {tx.counterparty}
              </div>
            )}
            {detail?.counterparty_address && (
              <div>
                <span className="font-medium text-gray-700">Adres: </span>
                {detail.counterparty_address}
              </div>
            )}
            {tx.description && (
              <div>
                <span className="font-medium text-gray-700">Opis: </span>
                {tx.description}
              </div>
            )}
            {detail?.source_account && (
              <div>
                <span className="font-medium text-gray-700">Konto źródłowe: </span>
                {detail.source_account}
              </div>
            )}
            {detail?.target_account && (
              <div>
                <span className="font-medium text-gray-700">Konto docelowe: </span>
                {detail.target_account}
              </div>
            )}
            <div>
                <span className="font-medium text-gray-700">Nr referencyjny: </span>
              <span className="font-mono">{tx.reference_number}</span>
            </div>
          </div>

          {/* Middle: candidates */}
          {candidates2.length > 0 && (
            <div className="w-80 space-y-1">
              <p className="text-xs font-medium text-gray-500 mb-2">
                Propozycje kategorii
              </p>
              {candidates2.map((c) => (
                <CandidateBar
                  key={c.category_id}
                  name={c.category_name}
                  score={c.category_score}
                />
              ))}
            </div>
          )}

          {/* Right: category picker + actions */}
          <div className="w-96 space-y-3">
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Kategoria</p>
              <CategoryDropdown
                value={selectedCategory}
                onChange={setSelectedCategory}
                candidates={candidates2.map((c) => ({
                  category_id: c.category_id,
                  category_name: c.category_name,
                  category_score: c.category_score,
                }))}
              />
            </div>
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
                  {reopenMutation.isPending ? "…" : "Otwórz ponownie"}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Tags section */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Tagi</p>
          <TagsEditor
            tags={detail?.tags ?? tx.tags ?? []}
            onChange={(tags) => tagsMutation.mutate(tags)}
            allTags={allTags}
          />
        </div>

        {/* Linked receipt section */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Powiązany paragon
          </p>

          {receiptLink ? (
            /* Existing link */
            <div className="flex items-center justify-between gap-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2">
              <Link
                href={`/receipts/${receiptLink.scan_id}`}
                className="text-xs space-y-0.5 hover:underline min-w-0"
                onClick={(e) => e.stopPropagation()}
              >
                <p className="font-medium text-[#635bff]">{receiptLink.vendor_name}</p>
                <p className="text-gray-500">
                  {receiptLink.date} · {receiptLink.total.toFixed(2)} PLN
                </p>
                <p className="text-gray-400 font-mono">{receiptLink.scan_filename}</p>
              </Link>
              <button
                disabled={unlinkMutation.isPending}
                onClick={() => unlinkMutation.mutate()}
                className="shrink-0 px-2 py-1 text-[10px] rounded-md border border-red-300 text-red-600
                           hover:bg-red-50 transition-colors disabled:opacity-40"
              >
                {unlinkMutation.isPending ? "…" : "Odepnij"}
              </button>
            </div>
          ) : showCandidates ? (
            /* Candidate list */
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
                    <button
                      disabled={linkMutation.isPending}
                      onClick={() => linkMutation.mutate(c.receipt_transaction_id)}
                      className="shrink-0 px-2 py-1 text-[10px] rounded-md bg-[#635bff] text-white
                                 hover:bg-[#4b44cc] transition-colors disabled:opacity-40"
                    >
                      {linkMutation.isPending ? "…" : "Powiąż"}
                    </button>
                  </div>
                ))}
              </div>
            )
          ) : (
            /* Button to trigger search */
            <button
              onClick={() => setShowCandidates(true)}
              className="text-xs px-3 py-1.5 rounded-md border border-[#635bff] text-[#635bff]
                         hover:bg-[#635bff]/10 transition-colors"
            >
              Znajdź pasujące paragony
            </button>
          )}
    </div>

        {/* Tags section */}
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Tagi</p>
          <TagsEditor
            tags={detail?.tags ?? tx.tags ?? []}
            onChange={(tags) => tagsMutation.mutate(tags)}
            allTags={allTags}
          />
        </div>
    </>
  );
}

export default function BankTransactionsPage() {
  const queryClient = useQueryClient();
  const PAGE_SIZE = 50;
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [sortBy, setSortBy] = useState("booking_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [importResult, setImportResult] = useState<BankImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ index: number; total: number } | null>(null);
  const [categorizingDone, setCategorizingDone] = useState(false);
  const channelRef = useRef<ReturnType<ReturnType<typeof getPusher>["subscribe"]> | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Cleanup Pusher on unmount
  useEffect(() => {
    return () => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
    };
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ["bank-transactions", page, statusFilter, sortBy, sortDir],
    queryFn: () => listBankTransactions({
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
    queryKey: ["bank-transactions-counts"],
    queryFn: getBankTransactionCounts,
    staleTime: 30_000,
  });
  const totalAll = Object.values(statusCounts).reduce<number>((sum, v) => sum + v, 0);

  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: getAllTags,
    staleTime: 60_000,
  });

  const importMutation = useMutation({
    mutationFn: importBankCsv,
    onSuccess: (result) => {
      setImportResult(result);
      setImportError(null);
      setCategorizingDone(false);
      setProgress(null);
      queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });

      if (result.task_id) {
        const pusher = getPusher();
        const channel = pusher.subscribe("bank-transactions");
        channelRef.current = channel;

        channel.bind(
          "categorization.progress",
          (data: { task_id: string; index: number; total: number }) => {
            if (data.task_id !== result.task_id) return;
            setProgress({ index: data.index, total: data.total });
          }
        );

        channel.bind(
          "categorization.done",
          (data: { task_id: string; total: number }) => {
            if (data.task_id !== result.task_id) return;
            setProgress(null);
            setCategorizingDone(true);
            channel.unbind_all();
            channel.unsubscribe();
            queryClient.invalidateQueries({ queryKey: ["bank-transactions"] });
            queryClient.invalidateQueries({ queryKey: ["bank-transactions-counts"] });
          }
        );

        channel.bind(
          "categorization.error",
          (data: { task_id: string; error: string }) => {
            if (data.task_id !== result.task_id) return;
            setProgress(null);
            setImportError(`Categorization error: ${data.error}`);
            channel.unbind_all();
            channel.unsubscribe();
          }
        );
      }
    },
    onError: (err: Error) => {
      setImportError(err.message);
      setImportResult(null);
    },
  });

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportResult(null);
    setImportError(null);
    setProgress(null);
    setCategorizingDone(false);
    importMutation.mutate(file);
    e.target.value = "";
  }

  const pct = progress ? Math.round((progress.index / progress.total) * 100) : 0;

  const columns: Column<BankTransactionListItem>[] = [
    {
      header: "Data",
      accessor: "booking_date",
      serverSortKey: "booking_date",
      className: "whitespace-nowrap text-gray-700",
    },
    {
      header: "Kontrahent / Opis",
      accessor: (t) => (
        <div>
          <div className="font-medium text-gray-800 truncate max-w-xs">
            {t.counterparty || "—"}
          </div>
          {t.description && (
            <div className="text-xs text-gray-400 truncate mt-0.5 max-w-xs">
              {t.description}
            </div>
          )}
        </div>
      ),
      serverSortKey: "counterparty",
    },
    {
      header: "Typ operacji",
      accessor: (t) => (
        <span className="text-gray-500 text-xs truncate max-w-[160px] block">
          {t.operation_type || "—"}
        </span>
      ),
      serverSortKey: "operation_type",
    },
    {
      header: "Kwota",
      accessor: (t) => (
        <span className={`font-mono font-medium whitespace-nowrap ${
          t.amount < 0 ? "text-red-600" : "text-green-600"
        }`}>
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
      header: "Tagi",
      accessor: (t) =>
        t.tags && t.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {t.tags.map((tag) => (
              <span key={tag} className="inline-block bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-full text-xs px-2 py-0.5 font-medium">
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
          Transakcje bankowe
        </h1>
        <div className="flex items-center gap-3">
          {/* Import feedback */}
          {importMutation.isPending && (
            <span className="text-sm text-gray-500">Importowanie…</span>
          )}
          {importResult && !importMutation.isPending && (
            <div className="flex flex-col gap-1 text-sm">
              <span className="text-gray-700">
                ✓ Zaimportowano: {importResult.imported}, duplikaty:{" "}
                {importResult.duplicates}
              </span>
              {progress && (
                <div className="flex flex-col gap-0.5 min-w-[220px]">
                  <span className="text-xs text-[#635bff] animate-pulse">
                    Kategoryzacja… {progress.index}/{progress.total}
                  </span>
                  <div className="w-full bg-gray-100 rounded-full h-1.5">
                    <div
                      className="h-1.5 rounded-full bg-[#635bff] transition-all duration-300"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              )}
              {categorizingDone && !progress && (
                <span className="text-xs text-green-600">
                  ✓ Kategoryzacja zakończona
                </span>
              )}
            </div>
          )}
          {importError && (
            <span className="text-sm text-red-600">Błąd: {importError}</span>
          )}

          {/* CSV upload button */}
          <input
            ref={fileRef}
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleFileChange}
          />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={importMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-[#635bff] text-white
                       text-sm font-medium hover:bg-[#4b44cc] transition-colors disabled:opacity-50"
          >
            <Upload className="h-4 w-4" />
            Import CSV
          </button>
        </div>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => { setStatusFilter(f); setPage(1); }}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
              statusFilter === f
                ? "border-[#635bff] text-[#635bff]"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {f === "all" ? "Wszystkie" : f === "to_confirm" ? "Do potwierdzenia" : "Potwierdzone"}
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
          emptyMessage="Brak transakcji. Zaimportuj plik CSV z banku."
          renderExpandedRow={(tx) => <ExpandedRowContent tx={tx} allTags={allTags} />}
          className="flex-1 min-h-0"
          pagination={{
            page, pageSize: PAGE_SIZE, total, onPageChange: setPage,
            sortBy, sortDir,
            onSortChange: (key, dir) => { setSortBy(key); setSortDir(dir); setPage(1); },
          }}
        />
      )}
    </div>
  );
}
