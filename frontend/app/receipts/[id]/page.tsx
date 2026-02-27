"use client";

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getReceipt, listCategories, confirmReceipt, reopenReceipt } from "@/lib/api";
import { ReceiptImageViewer } from "@/components/ReceiptImageViewer";
import { ProductCategoryRow } from "@/components/ProductCategoryRow";
import { StatusBadge } from "@/components/StatusBadge";
import { VendorDropdown } from "@/components/VendorDropdown";
import { ProductDropdown } from "@/components/ProductDropdown";
import { ProductItem } from "@/lib/types";
import Link from "next/link";

/** Convert YYYY-MM-DD (backend) → DD-MM-YYYY (display) */
function toDisplayDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  if (!y || !m || !d) return iso;
  return `${d}-${m}-${y}`;
}

/** Convert DD-MM-YYYY (display) → YYYY-MM-DD (backend) */
function toIsoDate(display: string): string {
  const [d, m, y] = display.split("-");
  if (!d || !m || !y) return display;
  return `${y}-${m}-${d}`;
}

export default function ReceiptReviewPage({
  params,
}: {
  params: { id: string };
}) {
  const scanId = Number(params.id);
  const queryClient = useQueryClient();

  const { data: scan, isLoading: scanLoading } = useQuery({
    queryKey: ["receipt", scanId],
    queryFn: () => getReceipt(scanId),
  });

  const { data: allCategories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: listCategories,
  });

  // Map: raw_product_name → selected category_id
  const [selections, setSelections] = useState<Record<string, number>>({});

  // Editable copies of OCR-sourced fields — initialised (and re-initialised) from
  // scan.result whenever it changes so navigation away and back preserves the data.
  const [editedVendor, setEditedVendor] = useState("");
  const [editedDate, setEditedDate] = useState("");
  const [editedTotal, setEditedTotal] = useState("");
  const [editedProducts, setEditedProducts] = useState<ProductItem[]>([]);
  // Editable normalized names — pre-filled from DB if an existing mapping exists.
  const [editedNormalizedVendor, setEditedNormalizedVendor] = useState("");
  const [editedNormalizedProducts, setEditedNormalizedProducts] = useState<Record<string, string>>({});
  // Separate string state for price inputs so the user can type freely without
  // the value being reformatted on every keystroke (type="text" + toFixed in value
  // would reset the cursor after each character).
  const [priceInputs, setPriceInputs] = useState<Array<{ unit: string; total: string }>>([])

  useEffect(() => {
    if (scan?.result) {
      setEditedVendor(scan.result.vendor);
      setEditedDate(toDisplayDate(scan.result.date));
      setEditedTotal(scan.result.total.toFixed(2));
      setEditedProducts(scan.result.products);
      setPriceInputs(
        scan.result.products.map((p) => ({
          unit: p.unit_price != null ? p.unit_price.toFixed(2) : "",
          total: p.price.toFixed(2),
        }))
      );
      setEditedNormalizedVendor(scan.vendor_normalization ?? "");
      setEditedNormalizedProducts(
        Object.fromEntries(
          Object.entries(scan.product_normalizations ?? {}).map(([k, v]) => [k, v ?? ""])
        )
      );
    }
  }, [scan?.result]);

  const confirmMutation = useMutation({
    mutationFn: (productCategories: Record<string, number>) =>
      confirmReceipt(scanId, {
        product_categories: productCategories,
        vendor: editedVendor || undefined,
        date: editedDate ? toIsoDate(editedDate) : undefined,
        total: editedTotal ? parseFloat(editedTotal) : undefined,
        products: editedProducts.length > 0 ? editedProducts : undefined,
        normalized_vendor: editedNormalizedVendor.trim() || undefined,
        normalized_products: (() => {
          const entries = Object.entries(editedNormalizedProducts).filter(([, v]) => v.trim() !== "");
          return entries.length > 0 ? Object.fromEntries(entries) : undefined;
        })(),
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(["receipt", scanId], updated);
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
    },
  });

  const reopenMutation = useMutation({
    mutationFn: () => reopenReceipt(scanId),
    onSuccess: (updated) => {
      queryClient.setQueryData(["receipt", scanId], updated);
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      setSelections({});
      // useEffect above will re-init the edited fields from updated.result
    },
  });

  if (scanLoading) {
    return (
      <div className="text-sm text-gray-400 py-16 text-center">Loading…</div>
    );
  }

  if (!scan) {
    return (
      <div className="text-sm text-red-500 py-16 text-center">
        Receipt not found.{" "}
        <Link href="/receipts" className="underline">
          Back
        </Link>
      </div>
    );
  }

  // Build candidates map: product_name → []
  const candidatesMap: Record<
    string,
    { category_id: number; category_name: string; category_score: number }[]
  > = {};

  if (scan.categories_candidates?.category_candidates) {
    for (const entry of scan.categories_candidates.category_candidates) {
      candidatesMap[entry.product_name] = entry.category_candidates;
    }
  }

  // Pre-seed selections from top candidate if not yet chosen
  const getSelection = (productName: string) => {
    if (selections[productName] !== undefined) return selections[productName];
    const candidates = candidatesMap[productName] ?? [];
    if (candidates.length > 0) {
      const top = [...candidates].sort(
        (a, b) => b.category_score - a.category_score
      )[0];
      return top.category_id;
    }
    return undefined;
  };

  const products = editedProducts.length > 0 ? editedProducts : (scan.result?.products ?? []);
  const allSelected = products.every(
    (p) => getSelection(p.name) !== undefined
  );

  const updateEditedProduct = (index: number, patch: Partial<ProductItem>) => {
    setEditedProducts((prev) =>
      prev.map((p, i) => (i === index ? { ...p, ...patch } : p))
    );
  };

  const updatePriceInput = (
    index: number,
    field: "unit" | "total",
    raw: string
  ) => {
    setPriceInputs((prev) =>
      prev.map((p, i) => (i === index ? { ...p, [field]: raw } : p))
    );
    // Keep editedProducts in sync so the header label and confirm payload stay accurate
    if (field === "unit") {
      updateEditedProduct(index, {
        unit_price: raw !== "" ? parseFloat(raw) || null : null,
      });
    } else {
      updateEditedProduct(index, { price: parseFloat(raw) || 0 });
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link
          href="/receipts"
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Receipts
        </Link>
        <h1 className="text-xl font-bold text-gray-900 flex-1 truncate">
          {scan.filename}
        </h1>
        <StatusBadge status={scan.status} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Receipt image */}
        <ReceiptImageViewer scanId={scanId} />

        {/* Review panel */}
        <div className="flex flex-col gap-4 overflow-y-auto max-h-[calc(100vh-10rem)] pr-1">
          {scan.transaction ? (
            /* Confirmed — read-only view */
            <>
              <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-2.5 flex items-center justify-between gap-2">
                <span className="text-green-600 font-semibold text-sm">✓ Confirmed</span>
                <button
                  onClick={() => reopenMutation.mutate()}
                  disabled={reopenMutation.isPending}
                  className="text-sm text-gray-500 hover:text-gray-700 underline disabled:opacity-50"
                >
                  {reopenMutation.isPending ? "Reopening…" : "Edit receipt"}
                </button>
              </div>

              <div className="rounded-xl border border-gray-200 p-4 space-y-1">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-semibold text-gray-900">
                    {scan.transaction.normalized_vendor_name ?? scan.transaction.raw_vendor_name}
                  </p>
                  <p className="font-bold text-gray-900 shrink-0">{scan.transaction.total.toFixed(2)} PLN</p>
                </div>
                {scan.transaction.normalized_vendor_name && scan.transaction.normalized_vendor_name !== scan.transaction.raw_vendor_name && (
                  <p className="text-xs text-gray-400">Raw: {scan.transaction.raw_vendor_name}</p>
                )}
                <p className="text-sm text-gray-500">{scan.transaction.date}</p>
              </div>

              <div className="space-y-2">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Products</h2>
                {scan.transaction.items.map((item) => {
                  const cat = allCategories.find((c) => c.id === item.category_id);
                  const catLabel = cat
                    ? [cat.group_name, cat.parent_name, cat.name].filter(Boolean).join(" / ")
                    : `Category #${item.category_id}`;
                  return (
                    <div key={item.id} className="flex flex-col gap-1 rounded-lg border border-gray-200 p-3 bg-white">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-900">
                          {item.normalized_product_name ?? item.raw_product_name}
                        </p>
                        <p className="text-sm font-semibold text-gray-900 shrink-0">{item.price.toFixed(2)} PLN</p>
                      </div>
                      {item.normalized_product_name && item.normalized_product_name !== item.raw_product_name && (
                        <p className="text-xs text-gray-400">Raw: {item.raw_product_name}</p>
                      )}
                      <p className="text-xs text-gray-500">
                        {item.quantity} × {(item.unit_price ?? item.price).toFixed(2)} PLN
                      </p>
                      <p className="text-xs text-[#635bff] font-medium">{catLabel}</p>
                    </div>
                  );
                })}
              </div>
            </>
          ) : (
            /* Editable — assign categories (and optionally edit OCR fields) */
            <>
              {/* Top-level OCR fields — always editable */}
              <div className="rounded-xl border border-gray-200 p-4 space-y-2">
                <label className="block text-xs text-gray-600">
                  Vendor
                  <input
                    type="text"
                    value={editedVendor}
                    onChange={(e) => setEditedVendor(e.target.value)}
                    className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                  />
                </label>
                <div className="block text-xs text-gray-600">
                  Normalized as
                  <VendorDropdown
                    value={editedNormalizedVendor}
                    onChange={setEditedNormalizedVendor}
                  />
                </div>
                <label className="block text-xs text-gray-600">
                  Date
                  <input
                    type="date"
                    value={toIsoDate(editedDate)}
                    onChange={(e) => setEditedDate(toDisplayDate(e.target.value))}
                    className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                  />
                </label>
                <label className="block text-xs text-gray-600">
                  Total (PLN)
                  <input
                    type="text"
                    inputMode="decimal"
                    value={editedTotal}
                    onChange={(e) => setEditedTotal(e.target.value)}
                    className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                  />
                </label>
              </div>

              <div className="space-y-2">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                  Assign categories
                </h2>
                {products.map((product, index) => (
                  <div key={product.name} className="rounded-lg border border-gray-200 bg-white">
                    {/* Product name + price — always visible at the top */}
                    <div className="px-3 pt-3 pb-2 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-900">{product.name}</p>
                        <p className="text-sm font-semibold text-gray-900 shrink-0">{product.price.toFixed(2)} PLN</p>
                      </div>
                      <p className="text-xs text-gray-500">
                        {product.quantity} × {(product.unit_price ?? product.price).toFixed(2)} PLN
                      </p>
                    </div>

                    {/* Numeric field editors */}
                    <div className="flex gap-2 px-3 pb-2 border-t border-gray-100">
                        <label className="flex-1 text-xs text-gray-600 pt-2">
                          Qty
                          <input
                            type="number"
                            step="0.001"
                            value={product.quantity}
                            onChange={(e) =>
                              updateEditedProduct(index, {
                                quantity: parseFloat(e.target.value) || 0,
                              })
                            }
                            className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                          />
                        </label>
                        <label className="flex-1 text-xs text-gray-600 pt-2">
                          Unit price
                          <input
                            type="text"
                            inputMode="decimal"
                            value={priceInputs[index]?.unit ?? ""}
                            onChange={(e) => updatePriceInput(index, "unit", e.target.value)}
                            className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                          />
                        </label>
                        <label className="flex-1 text-xs text-gray-600 pt-2">
                          Total price
                          <input
                            type="text"
                            inputMode="decimal"
                            value={priceInputs[index]?.total ?? ""}
                            onChange={(e) => updatePriceInput(index, "total", e.target.value)}
                            className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                          />
                        </label>
                      </div>

                    {/* Normalized product name */}
                    <div className="px-3 pb-2 border-t border-gray-100">
                      <div className="block text-xs text-gray-600 pt-2">
                        Normalized as
                        <ProductDropdown
                          value={editedNormalizedProducts[product.name] ?? ""}
                          onChange={(name) =>
                            setEditedNormalizedProducts((prev) => ({
                              ...prev,
                              [product.name]: name,
                            }))
                          }
                        />
                      </div>
                    </div>

                    {/* Category selector — hide built-in header since we render it above */}
                    <div className="[&>div]:rounded-none [&>div]:border-0 [&>div]:border-t [&>div]:border-gray-100">
                      <ProductCategoryRow
                        productName={product.name}
                        price={product.price}
                        quantity={product.quantity}
                        candidates={candidatesMap[product.name] ?? []}
                        allCategories={allCategories}
                        selectedCategoryId={getSelection(product.name)}
                        showHeader={false}
                        onChange={(categoryId) =>
                          setSelections((prev) => ({
                            ...prev,
                            [product.name]: categoryId,
                          }))
                        }
                      />
                    </div>
                  </div>
                ))}
              </div>

              <button
                disabled={!allSelected || confirmMutation.isPending}
                onClick={() => {
                  const resolved: Record<string, number> = {};
                  for (const p of products) {
                    const sel = getSelection(p.name);
                    if (sel !== undefined) resolved[p.name] = sel;
                  }
                  confirmMutation.mutate(resolved);
                }}
                className="mt-2 w-full py-2.5 rounded-md bg-[#635bff] text-white font-medium text-sm hover:bg-[#5248db] disabled:opacity-50 transition-colors"
              >
                {confirmMutation.isPending ? "Confirming…" : "Confirm receipt"}
              </button>

              {confirmMutation.isError && (
                <p className="text-sm text-red-500 text-center">
                  Failed to confirm. Please try again.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
