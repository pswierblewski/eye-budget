"use client";

import { useState, useEffect, useRef, useCallback, memo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listReceipts, processReceipts, deleteReceipt, retryReceipt, getReceiptCounts, getAllTags } from "@/lib/api";
import { ReceiptScanListItem } from "@/lib/types";
import { isoToDisplay } from "@/lib/utils";
import { DataTable, Column } from "@/components/DataTable";
import { getPusher } from "@/lib/pusher";
import { Info, SlidersHorizontal, X } from "lucide-react";
import Link from "next/link";
import { StatusBadge, Pill, PageHeader, NavLink, Button, FilterTabs, DateInput } from "@/components/ui";

const STATUS_FILTERS = [
  "all",
  "pending",
  "processing",
  "to_confirm",
  "done",
  "failed",
] as const;

const FILTER_LABELS: Record<string, string> = {
  all: "Wszystkie",
  pending: "Oczekujące",
  processing: "Przetwarzanie",
  to_confirm: "Do potwierdzenia",
  done: "Gotowe",
  failed: "Błąd",
};

type ProgressState = {
  index: number;
  total: number;
  filename: string;
  status: "running" | "done" | "error";
  errorMsg?: string;
};

const STATUS_LEGEND = [
  { status: "new", description: "Paragon dodany do systemu, oczekuje na przetworzenie." },
  { status: "processing", description: "Trwa rozpoznawanie tekstu (OCR) i analiza paragonu." },
  { status: "processed", description: "Analiza zakończona, oczekuje na weryfikację kategorii." },
  { status: "to_confirm", description: "Wymaga ręcznego potwierdzenia lub poprawienia kategorii." },
  { status: "done", description: "Paragon zweryfikowany i w pełni przetworzony." },
  { status: "failed", description: "Przetwarzanie nie powiodło się — sprawdź plik i spróbuj ponownie." },
] as const;

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

type FilterValues = {
  search: string;
  vendor: string;
  product: string;
  dateFrom: string;
  dateTo: string;
  totalMin: string;
  totalMax: string;
  tag: string;
};

const EMPTY_FILTERS: FilterValues = {
  search: "",
  vendor: "",
  product: "",
  dateFrom: "",
  dateTo: "",
  totalMin: "",
  totalMax: "",
  tag: "",
};

function countActive(f: FilterValues): number {
  return Object.values(f).filter(Boolean).length;
}

/* ------------------------------------------------------------------ */
/*  FilterPanel — isolated component, owns its own input state        */
/* ------------------------------------------------------------------ */

const FilterPanel = memo(function FilterPanel({
  onChange,
  onCountChange,
  allTags = [],
}: {
  onChange: (f: FilterValues) => void;
  onCountChange: (n: number) => void;
  allTags?: string[];
}) {
  const [local, setLocal] = useState<FilterValues>(EMPTY_FILTERS);

  const dSearch = useDebounce(local.search, 300);
  const dVendor = useDebounce(local.vendor, 300);
  const dProduct = useDebounce(local.product, 300);

  // Merge debounced text fields with instant date/number fields
  const applied: FilterValues = {
    search: dSearch,
    vendor: dVendor,
    product: dProduct,
    dateFrom: local.dateFrom,
    dateTo: local.dateTo,
    totalMin: local.totalMin,
    totalMax: local.totalMax,
    tag: local.tag,
  };

  const appliedRef = useRef(applied);
  useEffect(() => {
    const prev = appliedRef.current;
    if (
      prev.search !== applied.search ||
      prev.vendor !== applied.vendor ||
      prev.product !== applied.product ||
      prev.dateFrom !== applied.dateFrom ||
      prev.dateTo !== applied.dateTo ||
      prev.totalMin !== applied.totalMin ||
      prev.totalMax !== applied.totalMax ||
      prev.tag !== applied.tag
    ) {
      appliedRef.current = applied;
      onChange(applied);
      onCountChange(countActive(applied));
    }
  }, [applied, onChange, onCountChange]);

  // Also report initial count (0)
  useEffect(() => { onCountChange(0); }, [onCountChange]);

  const set = <K extends keyof FilterValues>(key: K, value: FilterValues[K]) =>
    setLocal((prev) => ({ ...prev, [key]: value }));

  const clear = () => setLocal(EMPTY_FILTERS);

  const hasAny = Object.values(local).some(Boolean);

  const INPUT = "w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus-ring";

  return (
    <div className="flex-shrink-0 rounded-lg border border-gray-200 bg-white p-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Nazwa paragonu</label>
          <input type="text" value={local.search} onChange={(e) => set("search", e.target.value)} placeholder="Szukaj po nazwie pliku lub sklepie…" className={INPUT} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Sklep</label>
          <input type="text" value={local.vendor} onChange={(e) => set("vendor", e.target.value)} placeholder="Nazwa raw lub znormalizowana…" className={INPUT} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Produkt</label>
          <input type="text" value={local.product} onChange={(e) => set("product", e.target.value)} placeholder="Nazwa raw lub znormalizowana…" className={INPUT} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Data od</label>
          <DateInput value={local.dateFrom} onChange={(iso) => set("dateFrom", iso)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Data do</label>
          <DateInput value={local.dateTo} onChange={(iso) => set("dateTo", iso)} />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">Tag</label>
          <input type="text" value={local.tag} onChange={(e) => set("tag", e.target.value)} placeholder="Filtruj po tagu…" list="filter-tags-datalist" className={INPUT} />
          {allTags.length > 0 && (
            <datalist id="filter-tags-datalist">
              {allTags.map((t) => <option key={t} value={t} />)}
            </datalist>
          )}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Suma od</label>
            <input type="number" step="0.01" min="0" value={local.totalMin} onChange={(e) => set("totalMin", e.target.value)} placeholder="0.00" className={INPUT} />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Suma do</label>
            <input type="number" step="0.01" min="0" value={local.totalMax} onChange={(e) => set("totalMax", e.target.value)} placeholder="999.99" className={INPUT} />
          </div>
        </div>
      </div>
      {hasAny && (
        <button onClick={clear} className="mt-3 inline-flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors">
          <X size={12} /> Wyczyść filtry
        </button>
      )}
    </div>
  );
});

export default function ReceiptsPage() {
  const queryClient = useQueryClient();
  const PAGE_SIZE = 50;
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState("id");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [progress, setProgress] = useState<ProgressState | null>(null);
  const [legendOpen, setLegendOpen] = useState(false);
  const channelRef = useRef<ReturnType<ReturnType<typeof getPusher>["subscribe"]> | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [bulkPending, setBulkPending] = useState<"delete" | "retry" | null>(null);
  const [bulkMenuOpen, setBulkMenuOpen] = useState(false);
  const bulkMenuRef = useRef<HTMLDivElement>(null);
  const legendRef = useRef<HTMLDivElement>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [activeFilterCount, setActiveFilterCount] = useState(0);

  const handleFiltersChange = useCallback((f: FilterValues) => {
    setAppliedFilters(f);
    setPage(1);
  }, []);

  const handleFilterCountChange = useCallback((n: number) => {
    setActiveFilterCount(n);
  }, []);

  // Cleanup Pusher subscription on unmount
  useEffect(() => {
    return () => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
    };
  }, []);

  useEffect(() => {
    if (!bulkMenuOpen) return;
    function handleClick(e: MouseEvent) {
      if (bulkMenuRef.current && !bulkMenuRef.current.contains(e.target as Node)) {
        setBulkMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [bulkMenuOpen]);

  useEffect(() => {
    if (!legendOpen) return;
    function handleClick(e: MouseEvent) {
      if (legendRef.current && !legendRef.current.contains(e.target as Node)) {
        setLegendOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [legendOpen]);

  const processMutation = useMutation({
    mutationFn: processReceipts,
    onSuccess: ({ task_id }) => {
      setProgress({ index: 0, total: 0, filename: "", status: "running" });

      const pusher = getPusher();
      const channel = pusher.subscribe("receipts");
      channelRef.current = channel;

      channel.bind("receipt.progress", (data: { task_id: string; index: number; total: number; filename: string; status: string }) => {
        if (data.task_id !== task_id) return;
        setProgress({ index: data.index, total: data.total, filename: data.filename, status: "running" });
      });

      channel.bind("receipt.done", (data: { task_id: string }) => {
        if (data.task_id !== task_id) return;
        setProgress((p) => p ? { ...p, status: "done" } : null);
        queryClient.invalidateQueries({ queryKey: ["receipts"] });
        queryClient.invalidateQueries({ queryKey: ["receipts-counts"] });
        channel.unbind_all();
        channel.unsubscribe();
      });

      channel.bind("receipt.error", (data: { task_id: string; error: string }) => {
        if (data.task_id !== task_id) return;
        setProgress((p) => p ? { ...p, status: "error", errorMsg: data.error } : null);
        channel.unbind_all();
        channel.unsubscribe();
      });
    },
  });

  const bulkDelete = async () => {
    if (!window.confirm(`Czy na pewno usunąć ${selectedIds.size} paragon${selectedIds.size !== 1 ? "ów" : ""}? Tej operacji nie można cofnąć.`)) return;
    setBulkPending("delete");
    await Promise.allSettled(Array.from(selectedIds).map((id) => deleteReceipt(id)));
    setSelectedIds(new Set());
    setBulkPending(null);
    queryClient.invalidateQueries({ queryKey: ["receipts"] });
    queryClient.invalidateQueries({ queryKey: ["receipts-counts"] });
  };

  const bulkRetry = async () => {
    setBulkPending("retry");
    await Promise.allSettled(Array.from(selectedIds).map((id) => retryReceipt(id)));
    setSelectedIds(new Set());
    setBulkPending(null);
    queryClient.invalidateQueries({ queryKey: ["receipts"] });
    queryClient.invalidateQueries({ queryKey: ["receipts-counts"] });
  };

  const { data, isLoading } = useQuery({
    queryKey: ["receipts", page, statusFilter, sortBy, sortDir, appliedFilters],
    queryFn: () => listReceipts({
      page,
      limit: PAGE_SIZE,
      status: statusFilter !== "all" ? statusFilter : undefined,
      sort_by: sortBy,
      sort_dir: sortDir,
      search: appliedFilters.search || undefined,
      vendor: appliedFilters.vendor || undefined,
      product: appliedFilters.product || undefined,
      date_from: appliedFilters.dateFrom || undefined,
      date_to: appliedFilters.dateTo || undefined,
      total_min: appliedFilters.totalMin ? parseFloat(appliedFilters.totalMin) : undefined,
      total_max: appliedFilters.totalMax ? parseFloat(appliedFilters.totalMax) : undefined,
      tag: appliedFilters.tag || undefined,
    }),
    staleTime: 30_000,
  });
  const receipts = data?.items ?? [];
  const total = data?.total ?? 0;

  const { data: statusCounts = {} } = useQuery({
    queryKey: ["receipts-counts"],
    queryFn: getReceiptCounts,
    staleTime: 30_000,
  });
  const totalAll = Object.values(statusCounts).reduce<number>((sum, v) => sum + v, 0);

  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: getAllTags,
    staleTime: 60_000,
  });

  const filtered = receipts;

  const allFilteredSelected = filtered.length > 0 && filtered.every((r) => selectedIds.has(r.id));

  const toggleAll = () => {
    if (allFilteredSelected) {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filtered.forEach((r) => next.delete(r.id));
        return next;
      });
    } else {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        filtered.forEach((r) => next.add(r.id));
        return next;
      });
    }
  };

  const columns: Column<ReceiptScanListItem>[] = [
    {
      header: "",
      headerNode: (
        <input
          type="checkbox"
          checked={allFilteredSelected}
          onChange={toggleAll}
          className="rounded border-gray-300 text-accent focus:ring-accent cursor-pointer"
        />
      ),
      accessor: (r) => (
        <input
          type="checkbox"
          checked={selectedIds.has(r.id)}
          onChange={() =>
            setSelectedIds((prev) => {
              const next = new Set(prev);
              if (next.has(r.id)) next.delete(r.id); else next.add(r.id);
              return next;
            })
          }
          onClick={(e) => e.stopPropagation()}
          className="rounded border-gray-300 text-accent focus:ring-accent cursor-pointer"
        />
      ),
      className: "w-10",
    },
    { header: "ID", accessor: "id", className: "w-16 text-gray-400 font-mono", serverSortKey: "id" },
    {
      header: "Plik",
      className: "w-48",
      accessor: (r) => (
        <Link
          href={`/receipts/${r.id}`}
          className="text-accent hover:underline font-medium truncate block"
        >
          {r.filename}
        </Link>
      ),
      serverSortKey: "filename",
    },
    {
      header: "Sklep",
      className: "w-48",
      accessor: (r) => (
        <span className="truncate block">
          {r.vendor ?? <span className="text-gray-400">—</span>}
        </span>
      ),
      serverSortKey: "vendor",
    },
    {
      header: "Data",
      className: "w-28 whitespace-nowrap",
      accessor: (r) => r.date
        ? <span className="font-mono text-xs text-gray-600 whitespace-nowrap">{isoToDisplay(r.date)}</span>
        : <span className="text-gray-400">—</span>,
      serverSortKey: "date",
    },
    {
      header: "Suma",
      accessor: (r) =>
        r.total != null ? (
          `${r.total.toFixed(2)} PLN`
        ) : (
          <span className="text-gray-400">—</span>
        ),
      className: "text-right whitespace-nowrap w-28",
      serverSortKey: "total",
    },
    {
      header: "Tagi",
      className: "w-40",
      accessor: (r) =>
        r.tags && r.tags.length > 0 ? (
          <div className="flex flex-wrap gap-1">
            {r.tags.map((tag) => (
              <Pill key={tag} variant="tag" size="sm">{tag}</Pill>
            ))}
          </div>
        ) : null,
    },
    {
      header: "Status",
      className: "w-36",
      accessor: (r) => <StatusBadge status={r.status} />,
      serverSortKey: "status",
    },
    {
      header: "",
      className: "w-24",
      accessor: (r) =>
        r.status === "to_confirm" ? (
          <NavLink
            href={`/receipts/${r.id}`}
            label="Przejrzyj"
            variant="forward"
            size="xs"
            onClick={(e) => e.stopPropagation()}
          />
        ) : null,
    },
  ];

  return (
    <div className="flex flex-col flex-1 min-h-0 gap-6">
      <PageHeader
        title={
          <span className="inline-flex items-center gap-2">
            Paragony
            <div ref={legendRef} className="relative">
              <button
                onClick={() => setLegendOpen((o) => !o)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
                aria-label="Legenda statusów"
              >
                <Info size={18} />
              </button>
              {legendOpen && (
                <div className="absolute left-0 top-full mt-2 z-50 w-96 rounded-lg border border-gray-200 bg-white shadow-lg p-4">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Legenda statusów</p>
                  <div className="grid grid-cols-1 gap-y-2">
                    {STATUS_LEGEND.map(({ status, description }) => (
                      <div key={status} className="flex items-start gap-2.5">
                        <StatusBadge status={status} />
                        <span className="text-xs text-gray-500 leading-5">{description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </span>
        }
        variant="list"
        subtitle="Wszystkie zeskanowane paragony i ich status przetwarzania."
        actions={
          <Button
            variant="primary"
            size="md"
            onClick={() => processMutation.mutate()}
            disabled={processMutation.isPending || progress?.status === "running"}
          >
            {processMutation.isPending || progress?.status === "running" ? "Przetwarzanie…" : "Przetwórz paragony"}
          </Button>
        }
      />

      {/* Live progress bar */}
      {progress && (
        <div className="flex-shrink-0 rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm">
          {progress.status === "running" && (
            <>
              <div className="flex justify-between mb-1 text-gray-600">
                <span>
                  {progress.total > 0
                    ? `Przetwarzanie ${progress.index} / ${progress.total} — ${progress.filename}`
                    : "Uruchamianie…"}
                </span>
                <span>{progress.total > 0 ? `${Math.round((progress.index / progress.total) * 100)}%` : ""}</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-1.5">
                <div
                  className="bg-accent h-1.5 rounded-full transition-all duration-300"
                  style={{ width: progress.total > 0 ? `${(progress.index / progress.total) * 100}%` : "0%" }}
                />
              </div>
            </>
          )}
          {progress.status === "done" && (
            <p className="text-green-600 font-medium">✓ Przetwarzanie zakończone — przetworzono {progress.total} paragon{progress.total !== 1 ? "ów" : ""}.</p>
          )}
          {progress.status === "error" && (
            <p className="text-red-600 font-medium">✗ Error: {progress.errorMsg}</p>
          )}
        </div>
      )}

      {/* Filter tabs + bulk actions — same row */}
      <div className="flex items-center gap-2 mt-4 mb-4 flex-wrap flex-shrink-0">
        <FilterTabs
          tabs={STATUS_FILTERS.map((s) => ({
            value: s,
            label: s === "all"
              ? <span>{FILTER_LABELS.all} <span className="ml-1 text-xs bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5">{totalAll}</span></span>
              : <span>{FILTER_LABELS[s] ?? s} <span className="ml-1 text-xs bg-gray-100 text-gray-600 rounded-full px-1.5 py-0.5">{statusCounts[s] ?? 0}</span></span>,
          }))}
          value={statusFilter}
          onChange={(v) => { setStatusFilter(v); setPage(1); setSelectedIds(new Set()); }}
        />

        <button
          onClick={() => setFiltersOpen((o) => !o)}
          className={`flex items-center gap-1.5 px-3 py-1.5 text-xs border rounded-lg transition-colors ${
            filtersOpen || activeFilterCount > 0
              ? "border-accent text-accent bg-accent/5"
              : "border-gray-200 text-gray-600 bg-white hover:bg-gray-50"
          }`}
        >
          <SlidersHorizontal size={13} />
          Filtry
          {activeFilterCount > 0 && (
            <span className="ml-0.5 inline-flex items-center justify-center w-4 h-4 rounded-full bg-accent/10 text-accent text-[10px] font-bold leading-none">
              {activeFilterCount}
            </span>
          )}
        </button>

        {activeFilterCount > 0 && (
          <button
            onClick={() => setFiltersOpen(true)}
            className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
          >
            <X size={12} />
            Wyczyść
          </button>
        )}

        {selectedIds.size > 0 && (
          <>
            <div className="w-px h-5 bg-gray-300 mx-1" />
            <span className="text-xs text-gray-500 font-medium">
              Zaznaczono: {selectedIds.size}
            </span>
            <button
              onClick={bulkRetry}
              disabled={bulkPending !== null}
              className="text-xs px-3 py-1.5 rounded-full border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {bulkPending === "retry" ? "Ponawiam…" : "Ponów przetwarzanie"}
            </button>
            <button
              onClick={() => setSelectedIds(new Set())}
              disabled={bulkPending !== null}
              className="text-xs text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
            >
              Odznacz
            </button>
            <div className="relative" ref={bulkMenuRef}>
              <button
                onClick={() => setBulkMenuOpen((o) => !o)}
                disabled={bulkPending !== null}
                className="text-xs px-2 py-1.5 rounded-full border border-gray-300 bg-white text-gray-700 hover:bg-gray-50 disabled:opacity-50 transition-colors leading-none"
                title="Więcej akcji"
              >
                ⋯
              </button>
              {bulkMenuOpen && (
                <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[160px]">
                  <button
                    type="button"
                    onClick={() => { setBulkMenuOpen(false); bulkDelete(); }}
                    disabled={bulkPending !== null}
                    className="w-full text-left px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                  >
                    {bulkPending === "delete" ? "Usuwam…" : "Usuń zaznaczone"}
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Advanced filters panel */}
      {filtersOpen && (
        <FilterPanel onChange={handleFiltersChange} onCountChange={handleFilterCountChange} allTags={allTags} />
      )}

      {isLoading ? (
        <div className="text-sm text-gray-400 py-8 text-center">Ładowanie…</div>
      ) : (
        <DataTable
          columns={columns}
          rows={filtered}
          emptyMessage="Brak paragonów spełniających filtr."
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
