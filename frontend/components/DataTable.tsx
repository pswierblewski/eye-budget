import { useState } from "react";

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
}: {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;
  className?: string;
}) {
  const [sortCol, setSortCol] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");

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
                colSpan={columns.length}
                className="px-4 py-8 text-center text-gray-400"
              >
                {emptyMessage}
              </td>
            </tr>
          ) : (
            sortedRows.map((row) => (
              <tr
                key={row.id}
                className="border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors"
              >
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
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
