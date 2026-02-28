import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

export type Column<T> = {
  header: string;
  accessor: keyof T | ((row: T) => React.ReactNode);
  sortValue?: (row: T) => string | number | null | undefined;
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
}: {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;
  className?: string;
  defaultSortCol?: string | null;
  defaultSortDir?: "asc" | "desc";
  renderExpandedRow?: (row: T) => React.ReactNode;
}) {
  const [sortCol, setSortCol] = useState<string | null>(defaultSortCol);
  const [sortDir, setSortDir] = useState<"asc" | "desc">(defaultSortDir);
  const [expandedId, setExpandedId] = useState<number | string | null>(null);

  function handleSort(header: string) {
    if (sortCol === header) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortCol(header);
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
      <table className="w-full text-sm">
        <thead className="sticky top-0 z-10">
          <tr className="border-b border-gray-200 bg-[#f6f9fc]">
            {renderExpandedRow && <th className="w-8 px-3 py-3" />}
            {columns.map((col) => {
              const sortable = !!col.sortValue;
              const isActive = sortCol === col.header;
              return (
                <th
                  key={col.header}
                  onClick={sortable ? () => handleSort(col.header) : undefined}
                  className={`px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 ${col.className ?? ""} ${sortable ? "cursor-pointer select-none hover:text-gray-800" : ""}`}
                >
                  <span className="inline-flex items-center gap-1">
                    {col.header}
                    {sortable && (
                      <span className={isActive ? "text-[#635bff]" : "text-gray-300"}>
                        {isActive && sortDir === "desc" ? "↓" : "↑"}
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
    </div>
  );
}
