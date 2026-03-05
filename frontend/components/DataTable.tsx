import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

export type Column<T> = {
  header: string;
  headerNode?: React.ReactNode;
  accessor: keyof T | ((row: T) => React.ReactNode);
  sortValue?: (row: T) => string | number | null | undefined;
  /** When set, clicking this column triggers server-side sort via pagination.onSortChange */
  serverSortKey?: string;
  className?: string;
};

export function DataTable<T extends { id: number | string }>({
  columns,
  rows,
  emptyMessage = "No data.",
  className = "",
  defaultSortCol = null,
  defaultSortDir = "asc",
  renderExpandedRow,
  pagination,
}: {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;
  className?: string;
  defaultSortCol?: string | null;
  defaultSortDir?: "asc" | "desc";
  renderExpandedRow?: (row: T) => React.ReactNode;
  pagination?: {
    page: number;
    pageSize: number;
    total: number;
    onPageChange: (page: number) => void;
    sortBy?: string;
    sortDir?: "asc" | "desc";
    onSortChange?: (key: string, dir: "asc" | "desc") => void;
  };
}) {
  const [sortCol, setSortCol] = useState<string | null>(defaultSortCol);
  const [sortDir, setSortDir] = useState<"asc" | "desc">(defaultSortDir);
  const [expandedId, setExpandedId] = useState<number | string | null>(null);

  function handleSort(col: Column<T>) {
    // Server-side sort
    if (col.serverSortKey && pagination?.onSortChange) {
      const currentKey = pagination.sortBy;
      const currentDir = pagination.sortDir ?? "desc";
      const newDir: "asc" | "desc" =
        currentKey === col.serverSortKey && currentDir === "desc" ? "asc" : "desc";
      pagination.onSortChange(col.serverSortKey, newDir);
      return;
    }
    // Local sort
    if (sortCol === col.header) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(col.header);
      setSortDir("asc");
    }
  }

  const sortedRows = [...rows];
  if (sortCol) {
    const col = columns.find((c) => c.header === sortCol);
    if (col?.sortValue) {
      sortedRows.sort((a, b) => {
        const va = col.sortValue!(a) ?? "";
        const vb = col.sortValue!(b) ?? "";
        if (va < vb) return sortDir === "asc" ? -1 : 1;
        if (va > vb) return sortDir === "asc" ? 1 : -1;
        return 0;
      });
    }
  }

  return (
    <div className={`w-full overflow-auto rounded-xl border border-gray-200 ${className}`}>
      <table className="w-full text-sm table-fixed">
        <thead className="sticky top-0 z-10">
          <tr className="border-b border-gray-200 bg-[#f6f9fc]">
            {renderExpandedRow && <th className="w-8 px-3 py-3" />}
            {columns.map((col) => {
              const sortable = !!col.sortValue || !!col.serverSortKey;
              const isActive = col.serverSortKey && pagination?.sortBy
                ? pagination.sortBy === col.serverSortKey
                : sortCol === col.header;
              const activeSortDir =
                col.serverSortKey && pagination?.sortBy === col.serverSortKey
                  ? (pagination.sortDir ?? "desc")
                  : sortDir;
              return (
                <th
                  key={col.header}
                  onClick={sortable ? () => handleSort(col) : undefined}
                  className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 ${col.className ?? ""} ${sortable ? "cursor-pointer select-none hover:text-gray-800" : ""}`}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.headerNode ?? col.header}
                    {sortable && (
                      <span className={isActive ? "text-[#635bff]" : "text-gray-300"}>
                        {isActive && activeSortDir === "desc" ? "↓" : "↑"}
                      </span>
                    )}
                  </span>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sortedRows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length + (renderExpandedRow ? 1 : 0)}
                className="px-4 py-8 text-center text-gray-400"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedRows.map((row) => (
              <Fragment key={row.id}>
                <tr
                  onClick={renderExpandedRow ? () => setExpandedId((prev) => (prev === row.id ? null : row.id)) : undefined}
                  className={`border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors ${renderExpandedRow ? "cursor-pointer" : ""}`}
                >
                  {renderExpandedRow && (
                    <td className="px-3 py-3 text-gray-400">
                      {expandedId === row.id
                        ? <ChevronDown className="h-4 w-4" />
                        : <ChevronRight className="h-4 w-4" />}
                    </td>
                  )}
                  {columns.map((col) => (
                    <td
                      key={col.header}
                      className={`px-4 py-3 ${col.className ?? ""}`}
                    >
                      {typeof col.accessor === "function"
                        ? col.accessor(row)
                        : String(row[col.accessor] ?? "")}
                    </td>
                  ))}
                </tr>
                {renderExpandedRow && expandedId === row.id && (
                  <tr className="bg-gray-50">
                    <td colSpan={columns.length + 1} className="px-6 py-4 border-b border-gray-100">
                      {renderExpandedRow(row)}
                    </td>
                  </tr>
                )}
              </Fragment>
            ))
          )}
        </tbody>
      </table>
      {pagination && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-[#f6f9fc] text-sm text-gray-600">
          <span className="text-xs">
            {pagination.total === 0
              ? "Brak wyników"
              : `${(pagination.page - 1) * pagination.pageSize + 1}–${Math.min(
                  pagination.page * pagination.pageSize,
                  pagination.total
                )} z ${pagination.total}`}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => pagination.onPageChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="px-2 py-1 rounded border border-gray-200 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed text-xs"
            >
              ‹
            </button>
            <span className="px-2 text-xs font-medium">
              {pagination.page} / {Math.max(1, Math.ceil(pagination.total / pagination.pageSize))}
            </span>
            <button
              onClick={() => pagination.onPageChange(pagination.page + 1)}
              disabled={pagination.page >= Math.ceil(pagination.total / pagination.pageSize)}
              className="px-2 py-1 rounded border border-gray-200 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed text-xs"
            >
              ›
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
