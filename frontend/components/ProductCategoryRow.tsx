"use client";

import { CategoryItem } from "@/lib/types";

type CategoryCandidate = {
  category_id: number;
  category_name: string;
  category_score: number;
};

export function ProductCategoryRow({
  productName,
  price,
  quantity,
  candidates,
  allCategories,
  selectedCategoryId,
  onChange,
  showHeader = true,
}: {
  productName: string;
  price: number;
  quantity: number;
  candidates: CategoryCandidate[];
  allCategories: CategoryItem[];
  selectedCategoryId: number | undefined;
  onChange: (categoryId: number) => void;
  showHeader?: boolean;
}) {
  const sortedCandidates = [...candidates].sort(
    (a, b) => b.category_score - a.category_score
  );

  const topCandidateIds = new Set(sortedCandidates.map((c) => c.category_id));

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-gray-200 p-3 bg-white">
      {showHeader && (
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900">
            {productName}
          </p>
          <p className="text-xs text-gray-500">
            {quantity} × {price.toFixed(2)} PLN
          </p>
        </div>
      )}
      <select
          value={selectedCategoryId ?? ""}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-[#635bff]"
      >
          <option value="" disabled>
            Select category…
          </option>
          {sortedCandidates.length > 0 && (
            <optgroup label="AI Suggestions">
              {sortedCandidates.map((c) => (
                <option key={c.category_id} value={c.category_id}>
                  {c.category_name} ({Math.round(c.category_score * 100)}%)
                </option>
              ))}
            </optgroup>
          )}
          <optgroup label="All Categories">
            {allCategories
              .filter((cat) => !topCandidateIds.has(cat.id))
              .map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.group_name ? `${cat.group_name} / ` : ""}
                  {cat.parent_name ? `${cat.parent_name} / ` : ""}
                  {cat.name}
                </option>
              ))}
          </optgroup>
        </select>
    </div>
  );
}
