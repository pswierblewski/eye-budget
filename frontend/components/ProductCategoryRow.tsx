"use client";

import { CategoryDropdown } from "@/components/CategoryDropdown";

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
  selectedCategoryId,
  onChange,
  showHeader = true,
}: {
  productName: string;
  price: number;
  quantity: number;
  candidates: CategoryCandidate[];
  selectedCategoryId: number | undefined;
  onChange: (categoryId: number) => void;
  showHeader?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-lg border border-gray-200 p-3 bg-white">
      {showHeader && (
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-900">{productName}</p>
          <p className="text-xs text-gray-500">
            {quantity} × {price.toFixed(2)} PLN
          </p>
        </div>
      )}
      <CategoryDropdown
        value={selectedCategoryId}
        onChange={onChange}
        candidates={candidates}
      />
    </div>
  );
}
