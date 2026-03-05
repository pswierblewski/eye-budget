"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getReceipt, listReceipts, listCategories, listProducts, confirmReceipt, reopenReceipt, deleteReceipt, retryReceipt, reuployReceiptImage, getBankTxCandidates, linkBankToReceipt, unlinkBankTransaction, updateReceiptTags, getAllTags, createCashFromReceipt, getCashTxCandidatesForReceipt, linkCashToReceipt, unlinkCashTransaction, updateTransactionItem, deleteTransactionItem } from "@/lib/api";
import { useRouter } from "next/navigation";
import { ReceiptImageViewer } from "@/components/ReceiptImageViewer";
import { ProductCategoryRow } from "@/components/ProductCategoryRow";
import { CategoryDropdown } from "@/components/CategoryDropdown";
import { StatusBadge, NavLink, Button, ConfirmDeleteModal, PrevNextNav, SectionLabel, Card, ThreeDotsMenu, DateInput } from "@/components/ui";
import { isoToDisplay } from "@/lib/utils";
import { VendorDropdown } from "@/components/VendorDropdown";
import { ProductDropdown } from "@/components/ProductDropdown";
import TagsEditor from "@/components/TagsEditor";
import { BankTxCandidateItem, CashTxCandidateItem, ProductItem, ReceiptTransactionItem } from "@/lib/types";
import Link from "next/link";

export default function ReceiptReviewPage({
  params,
}: {
  params: { id: string };
}) {
  const scanId = Number(params.id);
  const queryClient = useQueryClient();
  const router = useRouter();

  const { data: scan, isLoading: scanLoading } = useQuery({
    queryKey: ["receipt", scanId],
    queryFn: () => getReceipt(scanId),
  });

  const { data: allCategories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: listCategories,
  });

  // Inline editing of a single product on a confirmed receipt
  const [editingItemId, setEditingItemId] = useState<number | null>(null);
  const [editItemCategoryId, setEditItemCategoryId] = useState<number | undefined>(undefined);
  const [editItemNormalizedName, setEditItemNormalizedName] = useState("");
  const [editItemQuantity, setEditItemQuantity] = useState("");
  const [editItemUnitPrice, setEditItemUnitPrice] = useState("");
  const [editItemPrice, setEditItemPrice] = useState("");

  const { data: allProducts = [] } = useQuery({
    queryKey: ["products"],
    queryFn: listProducts,
    enabled: editingItemId !== null,
  });

  const { data: allReceipts } = useQuery({
    queryKey: ["receipts", "all", "nav"],
    queryFn: () => listReceipts({ limit: 1000 }),
  });

  const { prevReceiptId, nextReceiptId } = (() => {
    if (!allReceipts) return { prevReceiptId: null, nextReceiptId: null };
    const ids = allReceipts.items.map((r) => r.id).sort((a, b) => a - b);
    const idx = ids.indexOf(scanId);
    return {
      prevReceiptId: idx > 0 ? ids[idx - 1] : null,
      nextReceiptId: idx !== -1 && idx < ids.length - 1 ? ids[idx + 1] : null,
    };
  })();

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
  const [openMenuIndex, setOpenMenuIndex] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [productSearch, setProductSearch] = useState("");
  const [confirmedMenuItemId, setConfirmedMenuItemId] = useState<number | null>(null);
  const [confirmDeleteItemId, setConfirmDeleteItemId] = useState<number | null>(null);
  const confirmedMenuRef = useRef<HTMLDivElement>(null);

  // Close confirmed-item three-dot menu on outside click
  useEffect(() => {
    if (confirmedMenuItemId === null) return;
    function handleClick(e: MouseEvent) {
      if (confirmedMenuRef.current && !confirmedMenuRef.current.contains(e.target as Node)) {
        setConfirmedMenuItemId(null);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [confirmedMenuItemId]);

  const startEditingItem = (item: ReceiptTransactionItem) => {
    setEditingItemId(item.id);
    setEditItemCategoryId(item.category_id);
    setEditItemNormalizedName(item.normalized_product_name ?? "");
    setEditItemQuantity(String(item.quantity));
    setEditItemUnitPrice(item.unit_price != null ? item.unit_price.toFixed(2) : "");
    setEditItemPrice(item.price.toFixed(2));
  };

  const cancelEditingItem = () => {
    setEditingItemId(null);
  };

  const updateItemMutation = useMutation({
    mutationFn: (args: { itemId: number; data: Partial<{ category_id: number; product_id: number; quantity: number; unit_price: number; price: number }> }) =>
      updateTransactionItem(args.itemId, args.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipt", scanId] });
      setEditingItemId(null);
    },
  });

  const deleteItemMutation = useMutation({
    mutationFn: (itemId: number) => deleteTransactionItem(itemId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipt", scanId] });
      setConfirmedMenuItemId(null);
    },
  });

  useEffect(() => {
    if (openMenuIndex === null) return;
    function handleClick(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setOpenMenuIndex(null);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [openMenuIndex]);

  useEffect(() => {
    if (scan?.result) {
      setProductSearch("");
      setEditedVendor(scan.result.vendor);
      setEditedDate(scan.result.date);
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
        date: editedDate || undefined,
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
    mutationFn: async () => {
      // Capture confirmed categories BEFORE the backend deletes the transaction.
      // This preserves both manually-added product categories (which have no entry
      // in categories_candidates) and any user overrides of AI-suggested categories.
      const confirmedSelections: Record<string, number> = {};
      if (scan?.transaction?.items) {
        for (const item of scan.transaction.items) {
          confirmedSelections[item.raw_product_name] = item.category_id;
        }
      }
      const updated = await reopenReceipt(scanId);
      return { updated, confirmedSelections };
    },
    onSuccess: ({ updated, confirmedSelections }) => {
      queryClient.setQueryData(["receipt", scanId], updated);
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      setSelections(confirmedSelections);
      // useEffect above will re-init the edited fields from updated.result
    },
  });

  const [showBankCandidates, setShowBankCandidates] = useState(false);

  const { data: bankCandidates = [], isFetching: bankCandidatesLoading } = useQuery<BankTxCandidateItem[]>({
    queryKey: ["receipt-bank-candidates", scanId],
    queryFn: () => getBankTxCandidates(scanId),
    enabled: showBankCandidates,
  });

  const linkBankMutation = useMutation({
    mutationFn: (bankTxId: number) =>
      linkBankToReceipt(bankTxId, scan!.transaction!.id),
    onSuccess: (updated) => {
      // updated is BankTransactionDetail — but we re-fetch the scan to get bank_link
      queryClient.invalidateQueries({ queryKey: ["receipt", scanId] });
      queryClient.invalidateQueries({ queryKey: ["receipt-bank-candidates", scanId] });
      setShowBankCandidates(false);
    },
  });

  const unlinkBankMutation = useMutation({
    mutationFn: (bankTxId: number) => unlinkBankTransaction(bankTxId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipt", scanId] });
    },
  });

  const [showCashCandidates, setShowCashCandidates] = useState(false);

  const { data: cashCandidates = [], isFetching: cashCandidatesLoading } = useQuery<CashTxCandidateItem[]>({
    queryKey: ["receipt-cash-candidates", scanId],
    queryFn: () => getCashTxCandidatesForReceipt(scanId),
    enabled: showCashCandidates,
  });

  const createCashMutation = useMutation({
    mutationFn: () => createCashFromReceipt(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipt", scanId] });
    },
  });

  const linkCashMutation = useMutation({
    mutationFn: (cashTxId: number) =>
      linkCashToReceipt(cashTxId, scan!.transaction!.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipt", scanId] });
      queryClient.invalidateQueries({ queryKey: ["receipt-cash-candidates", scanId] });
      setShowCashCandidates(false);
    },
  });

  const unlinkCashMutation = useMutation({
    mutationFn: (cashTxId: number) => unlinkCashTransaction(cashTxId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipt", scanId] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteReceipt(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      router.push("/receipts");
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => retryReceipt(scanId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["receipt", scanId] });
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
    },
  });

  const { data: allTags = [] } = useQuery({
    queryKey: ["tags"],
    queryFn: getAllTags,
    staleTime: 60_000,
  });

  const tagsMutation = useMutation({
    mutationFn: (tags: string[]) => updateReceiptTags(scanId, tags),
    onSuccess: (updated) => {
      queryClient.setQueryData(["receipt", scanId], updated);
      queryClient.invalidateQueries({ queryKey: ["receipts"] });
      queryClient.invalidateQueries({ queryKey: ["tags"] });
    },
  });

  const [imageRefreshKey, setImageRefreshKey] = useState(0);
  const handleReuloadImage = async () => {
    await reuployReceiptImage(scanId);
    setImageRefreshKey((k) => k + 1);
  };

  if (scanLoading) {
    return (
      <div className="text-sm text-gray-400 py-16 text-center">Ładowanie…</div>
    );
  }

  if (!scan) {
    return (
      <div className="text-sm text-red-500 py-16 text-center">
        Nie znaleziono paragonu.{" "}
        <Link href="/receipts" className="underline">
          Wróć
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

  // Calculated total from product prices
  const calculatedTotal = editedProducts.reduce((sum, p) => sum + (p.price || 0), 0);
  const parsedTotal = parseFloat(editedTotal) || 0;
  const totalsMatch = Math.abs(calculatedTotal - parsedTotal) < 0.005;

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

  const addProduct = () => {
    const newProduct: ProductItem = { name: "", quantity: 1, price: 0, unit_price: null };
    setEditedProducts((prev) => [...prev, newProduct]);
    setPriceInputs((prev) => [...prev, { unit: "", total: "0.00" }]);
  };

  const removeProduct = (index: number) => {
    const removedName = editedProducts[index]?.name;
    setEditedProducts((prev) => prev.filter((_, i) => i !== index));
    setPriceInputs((prev) => prev.filter((_, i) => i !== index));
    if (removedName) {
      setSelections((prev) => {
        const next = { ...prev };
        delete next[removedName];
        return next;
      });
      setEditedNormalizedProducts((prev) => {
        const next = { ...prev };
        delete next[removedName];
        return next;
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Confirm Delete Modal */}
      <ConfirmDeleteModal
        open={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={() => deleteMutation.mutate()}
        title="Usuń paragon"
        description="Paragon i powiązane dane zostaną trwale usunięte."
        loading={deleteMutation.isPending}
      />

      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <NavLink href="/receipts" label="Paragony" variant="back" size="xs" />
        <span className="text-gray-300">/</span>
        <h1 className="text-xl font-bold text-gray-900 flex-1 truncate">
          {scan.filename}
        </h1>
        <span className="text-xs text-gray-400 font-mono shrink-0">#{scanId}</span>
        <StatusBadge status={scan.status} />
        {["new", "processing", "processed", "failed"].includes(scan.status) && (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => retryMutation.mutate()}
            disabled={retryMutation.isPending}
          >
            {retryMutation.isPending ? "Ponawiam…" : "Ponów przetwarzanie"}
          </Button>
        )}
        <PrevNextNav
          hasPrev={prevReceiptId !== null}
          hasNext={nextReceiptId !== null}
          onPrev={() => prevReceiptId && router.push(`/receipts/${prevReceiptId}`)}
          onNext={() => nextReceiptId && router.push(`/receipts/${nextReceiptId}`)}
        />
        <ThreeDotsMenu
          variant="outlined"
          items={[
            { label: "Usuń paragon", variant: "danger", onClick: () => setShowDeleteModal(true) },
          ]}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Receipt image */}
        <ReceiptImageViewer
          scanId={scanId}
          refreshKey={imageRefreshKey}
          onReuploadImage={handleReuloadImage}
        />

        {/* Review panel */}
        <div className="flex flex-col gap-4 overflow-y-auto max-h-[calc(100vh-10rem)] pr-1">
          {scan.transaction ? (
            /* Confirmed — read-only view */
            <>
              <div className="rounded-xl border border-green-200 bg-green-50 px-4 py-2.5 flex items-center justify-between gap-2">
                <span className="text-green-600 font-semibold text-sm">✓ Potwierdzono</span>
                <button
                  onClick={() => reopenMutation.mutate()}
                  disabled={reopenMutation.isPending}
                  className="text-sm text-gray-500 hover:text-gray-700 underline disabled:opacity-50"
                >
                  {reopenMutation.isPending ? "Otwieranie…" : "Edytuj paragon"}
                </button>
              </div>

              {/* Bank transaction link section */}
              <div className="rounded-xl border border-gray-200 p-4 space-y-2">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                  Transakcja bankowa
                </h2>

                {scan.bank_link ? (
                  /* Existing link */
                  <div className="flex items-center justify-between gap-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2">
                    <Link
                      href={`/bank-transactions/${scan.bank_link.bank_transaction_id}`}
                      className="text-xs space-y-0.5 hover:underline min-w-0"
                    >
                      <p className="font-medium text-accent">
                        {scan.bank_link.counterparty ?? "—"}
                      </p>
                      <p className="text-gray-500">
                        {scan.bank_link.booking_date} · {scan.bank_link.amount.toFixed(2)} PLN
                      </p>
                    </Link>
                    <button
                      disabled={unlinkBankMutation.isPending}
                      onClick={() => unlinkBankMutation.mutate(scan.bank_link!.bank_transaction_id)}
                      className="shrink-0 px-2 py-1 text-[10px] rounded-md border border-red-300
                                 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                    >
                      {unlinkBankMutation.isPending ? "…" : "Odepnij"}
                    </button>
                  </div>
                ) : showBankCandidates ? (
                  /* Candidate list */
                  bankCandidatesLoading ? (
                    <p className="text-xs text-gray-400 animate-pulse">Szukanie…</p>
                  ) : bankCandidates.length === 0 ? (
                    <p className="text-xs text-gray-400 italic">
                      Nie znaleziono pasujących transakcji bankowych.
                    </p>
                  ) : (
                    <div className="space-y-1.5">
                      {bankCandidates.map((c) => {
                        const scoreLabel =
                          c.match_score >= 3 ? "kwota + data + sklep" : "kwota + data";
                        const scoreColor =
                          c.match_score >= 3
                            ? "bg-green-100 text-green-700"
                            : "bg-yellow-100 text-yellow-700";
                        return (
                          <div
                            key={c.bank_transaction_id}
                            className="flex items-center justify-between gap-3 rounded-lg border
                                       border-gray-200 bg-white px-3 py-2"
                          >
                            <div className="text-xs space-y-0.5 min-w-0">
                              <div className="flex items-center gap-2">
                                <p className="font-medium text-gray-800 truncate">
                                  {c.counterparty ?? "—"}
                                </p>
                                <span
                                  className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${scoreColor}`}
                                >
                                  {scoreLabel}
                                </span>
                              </div>
                              <p className="text-gray-500">
                                {c.booking_date} · {c.amount.toFixed(2)} PLN
                              </p>
                            </div>
                            <button
                              disabled={linkBankMutation.isPending}
                              onClick={() => linkBankMutation.mutate(c.bank_transaction_id)}
                              className="shrink-0 px-2 py-1 text-[10px] rounded-md bg-accent
                                         text-white hover:bg-accent-hover transition-colors disabled:opacity-50"
                            >
                              {linkBankMutation.isPending ? "…" : "Powiąż"}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )
                ) : scan.cash_link ? (
                  <p className="text-xs text-gray-400 italic">
                    Odepnij transakcję gotówkową, aby powiązać z transakcją bankową.
                  </p>
                ) : (
                  /* Trigger button */
                  <button
                    onClick={() => setShowBankCandidates(true)}
                    className="text-xs px-3 py-1.5 rounded-md border border-accent text-accent
                               hover:bg-accent/10 transition-colors"
                  >
                    Znajdź pasującą transakcję bankową
                  </button>
                )}
              </div>

              {/* Cash transaction section */}
              <div className="rounded-xl border border-gray-200 p-4 space-y-2">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                  Transakcja gotówkowa
                </h2>

                {scan.cash_link ? (
                  <div className="flex items-center justify-between gap-4 rounded-lg border border-green-200 bg-green-50 px-3 py-2">
                    <Link
                      href="/cash-transactions"
                      className="text-xs space-y-0.5 hover:underline min-w-0"
                    >
                      <p className="font-medium text-accent">
                        {scan.cash_link.description ?? "Transakcja gotówkowa"}
                      </p>
                      <p className="text-gray-500">
                        {scan.cash_link.booking_date} · {scan.cash_link.amount.toFixed(2)} PLN
                      </p>
                    </Link>
                    <button
                      disabled={unlinkCashMutation.isPending}
                      onClick={() => unlinkCashMutation.mutate(scan.cash_link!.cash_transaction_id)}
                      className="shrink-0 px-2 py-1 text-[10px] rounded-md border border-red-300
                                 text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                    >
                      {unlinkCashMutation.isPending ? "…" : "Odepnij"}
                    </button>
                  </div>
                ) : scan.bank_link ? (
                  <p className="text-xs text-gray-400 italic">
                    Odepnij transakcję bankową, aby powiązać z transakcją gotówkową.
                  </p>
                ) : scan.transaction ? (
                  <div className="space-y-2">
                    <button
                      onClick={() => createCashMutation.mutate()}
                      disabled={createCashMutation.isPending}
                      className="text-xs px-3 py-1.5 rounded-md bg-accent text-white
                                 hover:bg-accent-hover transition-colors disabled:opacity-50"
                    >
                      {createCashMutation.isPending ? "Tworzenie…" : "Utwórz transakcję gotówkową"}
                    </button>
                    {!showCashCandidates ? (
                      <button
                        onClick={() => setShowCashCandidates(true)}
                        className="block text-xs px-3 py-1.5 rounded-md border border-accent text-accent
                                   hover:bg-accent/10 transition-colors"
                      >
                        Powiąż z istniejącą transakcją gotówkową
                      </button>
                    ) : cashCandidatesLoading ? (
                      <p className="text-xs text-gray-400 animate-pulse">Szukanie…</p>
                    ) : cashCandidates.length === 0 ? (
                      <p className="text-xs text-gray-400 italic">Brak pasujących transakcji.</p>
                    ) : (
                      <div className="space-y-1.5">
                        {cashCandidates.map((c) => (
                          <div key={c.cash_transaction_id}
                               className="flex items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white px-3 py-2">
                            <div className="text-xs space-y-0.5 min-w-0">
                              <p className="font-medium text-gray-800">{c.description ?? "—"}</p>
                              <p className="text-gray-500">{c.booking_date} · {c.amount.toFixed(2)} PLN</p>
                            </div>
                            <button
                              disabled={linkCashMutation.isPending}
                              onClick={() => linkCashMutation.mutate(c.cash_transaction_id)}
                              className="shrink-0 px-2 py-1 text-[10px] rounded-md bg-accent
                                         text-white hover:bg-accent-hover transition-colors disabled:opacity-50"
                            >
                              {linkCashMutation.isPending ? "…" : "Powiąż"}
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 italic">
                    Potwierdź paragon najpierw, aby powiązać z transakcją gotówkową.
                  </p>
                )}
              </div>

              {/* Tags section */}
              <div className="rounded-xl border border-gray-200 p-4 space-y-2">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Tagi</h2>
                <TagsEditor
                  tags={scan.tags ?? []}
                  onChange={(tags) => tagsMutation.mutate(tags)}
                  allTags={allTags}
                />
              </div>

              <div className="rounded-xl border border-gray-200 p-4 space-y-1">
                {(() => {
                  const confirmedCalc = scan.transaction.items.reduce((s, i) => s + i.price, 0);
                  const confirmedMatch = Math.abs(confirmedCalc - scan.transaction.total) < 0.005;
                  const diff = scan.transaction.total - confirmedCalc;
                  return (
                    <>
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-semibold text-gray-900">
                          {scan.transaction.normalized_vendor_name ?? scan.transaction.raw_vendor_name}
                        </p>
                        <div className="flex flex-col items-end gap-0.5 shrink-0">
                          <span className="font-bold text-gray-900">{scan.transaction.total.toFixed(2)} PLN</span>
                          <span className="text-xs text-gray-400">z produktów: {confirmedCalc.toFixed(2)} PLN</span>
                          {confirmedMatch ? (
                            <span className="inline-flex items-center text-[10px] font-semibold text-green-700 bg-green-100 px-1.5 py-0.5 rounded-full" title="Sumy się zgadzają">✓ zgodne</span>
                          ) : (
                            <span className="inline-flex items-center text-[10px] font-semibold text-red-600 bg-red-100 px-1.5 py-0.5 rounded-full" title="Sumy się nie zgadzają">✗ różnica {diff > 0 ? "+" : ""}{diff.toFixed(2)} PLN</span>
                          )}
                        </div>
                      </div>
                    </>
                  );
                })()}
                {scan.transaction.normalized_vendor_name && scan.transaction.normalized_vendor_name !== scan.transaction.raw_vendor_name && (
                  <p className="text-xs text-gray-400">Raw: {scan.transaction.raw_vendor_name}</p>
                )}
                <p className="text-sm text-gray-500">{isoToDisplay(scan.transaction.date)}</p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Produkty</h2>
                  {productSearch && (
                    <span className="text-xs text-gray-400">
                      {scan.transaction.items.filter((i) =>
                        [i.normalized_product_name, i.raw_product_name]
                          .filter(Boolean)
                          .some((n) => n!.toLowerCase().includes(productSearch.toLowerCase()))
                      ).length}{" / "}{scan.transaction.items.length}
                    </span>
                  )}
                </div>
                {scan.transaction.items.length > 5 && (
                  <input
                    type="search"
                    value={productSearch}
                    onChange={(e) => setProductSearch(e.target.value)}
                    placeholder="Szukaj produktu…"
                    className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                )}
                {scan.transaction.items
                  .filter((i) =>
                    !productSearch ||
                    [i.normalized_product_name, i.raw_product_name]
                      .filter(Boolean)
                      .some((n) => n!.toLowerCase().includes(productSearch.toLowerCase()))
                  )
                  .map((item) => {
                  const cat = allCategories.find((c) => c.id === item.category_id);
                  const catLabel = cat
                    ? [cat.group_name, cat.parent_name, cat.name].filter(Boolean).join(" / ")
                    : `Category #${item.category_id}`;

                  if (editingItemId === item.id) {
                    return (
                      <div key={item.id} className="flex flex-col gap-2 rounded-lg border-2 border-accent p-3 bg-indigo-50/30">
                        {/* Product name (read-only raw name) */}
                        <p className="text-sm font-medium text-gray-900">
                          {item.normalized_product_name ?? item.raw_product_name}
                        </p>
                        {item.normalized_product_name && item.normalized_product_name !== item.raw_product_name && (
                          <p className="text-xs text-gray-400">Raw: {item.raw_product_name}</p>
                        )}

                        {/* Normalized product (ProductDropdown) */}
                        <div>
                          <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Produkt znormalizowany</label>
                          <ProductDropdown
                            value={editItemNormalizedName}
                            onChange={(name) => setEditItemNormalizedName(name)}
                          />
                        </div>

                        {/* Category */}
                        <div>
                          <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Kategoria</label>
                          <CategoryDropdown
                            value={editItemCategoryId}
                            onChange={(id) => setEditItemCategoryId(id)}
                          />
                        </div>

                        {/* Quantity / Unit price / Total price */}
                        <div className="grid grid-cols-3 gap-2">
                          <div>
                            <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Ilość</label>
                            <input
                              type="text"
                              inputMode="decimal"
                              value={editItemQuantity}
                              onChange={(e) => setEditItemQuantity(e.target.value)}
                              className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Cena jedn.</label>
                            <input
                              type="text"
                              inputMode="decimal"
                              value={editItemUnitPrice}
                              onChange={(e) => setEditItemUnitPrice(e.target.value)}
                              className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                            />
                          </div>
                          <div>
                            <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">Cena</label>
                            <input
                              type="text"
                              inputMode="decimal"
                              value={editItemPrice}
                              onChange={(e) => setEditItemPrice(e.target.value)}
                              className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                            />
                          </div>
                        </div>

                        {/* Save / Cancel */}
                        <div className="flex gap-2 pt-1">
                          <button
                            onClick={cancelEditingItem}
                            className="flex-1 px-3 py-1.5 text-xs rounded-md border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors"
                          >
                            Anuluj
                          </button>
                          <button
                            disabled={updateItemMutation.isPending}
                            onClick={() => {
                              const data: Partial<{ category_id: number; product_id: number; quantity: number; unit_price: number; price: number }> = {};
                              if (editItemCategoryId !== undefined && editItemCategoryId !== item.category_id) {
                                data.category_id = editItemCategoryId;
                              }
                              // Resolve normalized product name to product_id
                              const currentNormName = item.normalized_product_name ?? "";
                              if (editItemNormalizedName !== currentNormName) {
                                const matched = allProducts.find(
                                  (p) => p.name.toLowerCase() === editItemNormalizedName.trim().toLowerCase()
                                );
                                if (matched) data.product_id = matched.id;
                              }
                              const q = parseFloat(editItemQuantity.replace(",", "."));
                              if (!isNaN(q) && q !== item.quantity) data.quantity = q;
                              const up = parseFloat(editItemUnitPrice.replace(",", "."));
                              if (!isNaN(up) && up !== item.unit_price) data.unit_price = up;
                              const p = parseFloat(editItemPrice.replace(",", "."));
                              if (!isNaN(p) && p !== item.price) data.price = p;
                              if (Object.keys(data).length === 0) {
                                cancelEditingItem();
                                return;
                              }
                              updateItemMutation.mutate({ itemId: item.id, data });
                            }}
                            className="flex-1 px-3 py-1.5 text-xs rounded-md bg-accent text-white font-medium hover:bg-accent-hover transition-colors disabled:opacity-50"
                          >
                            {updateItemMutation.isPending ? "Zapisywanie…" : "Zapisz"}
                          </button>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div key={item.id} className="flex flex-col gap-1 rounded-lg border border-gray-200 p-3 bg-white">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-gray-900">
                          {item.normalized_product_name ?? item.raw_product_name}
                        </p>
                        <div className="flex items-center gap-1 shrink-0">
                          <p className="text-sm font-semibold text-gray-900">{item.price.toFixed(2)} PLN</p>
                          <div className="relative" ref={confirmedMenuItemId === item.id ? confirmedMenuRef : undefined}>
                            <button
                              type="button"
                              onClick={() => setConfirmedMenuItemId(confirmedMenuItemId === item.id ? null : item.id)}
                              className="p-1 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors leading-none"
                              title="Opcje"
                            >
                              ⋯
                            </button>
                            {confirmedMenuItemId === item.id && (
                              <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[150px]">
                                <button
                                  type="button"
                                  onClick={() => { startEditingItem(item); setConfirmedMenuItemId(null); }}
                                  className="w-full text-left px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                                >
                                  Edytuj produkt
                                </button>
                                <button
                                  type="button"
                                  disabled={deleteItemMutation.isPending}
                                  onClick={() => { setConfirmedMenuItemId(null); setConfirmDeleteItemId(item.id); }}
                                  className="w-full text-left px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 transition-colors disabled:opacity-50"
                                >
                                  Usuń produkt
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                      {item.normalized_product_name && item.normalized_product_name !== item.raw_product_name && (
                        <p className="text-xs text-gray-400">Raw: {item.raw_product_name}</p>
                      )}
                      <p className="text-xs text-gray-500">
                        {item.quantity} × {(item.unit_price ?? item.price).toFixed(2)} PLN
                      </p>
                      <p className="text-xs text-accent font-medium">{catLabel}</p>
                    </div>
                  );
                })}
              </div>

              {/* Delete product confirmation dialog */}
              {confirmDeleteItemId !== null && (() => {
                const delItem = scan.transaction.items.find((i) => i.id === confirmDeleteItemId);
                return (
                  <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40">
                    <div className="bg-white rounded-xl shadow-xl p-5 max-w-sm w-full mx-4 space-y-3">
                      <h3 className="text-sm font-semibold text-gray-900">Usunąć produkt?</h3>
                      {delItem && (
                        <p className="text-sm text-gray-600">
                          <span className="font-medium">{delItem.normalized_product_name ?? delItem.raw_product_name}</span>
                          {" — "}{delItem.price.toFixed(2)} PLN
                        </p>
                      )}
                      <p className="text-xs text-gray-400">Tej operacji nie można cofnąć.</p>
                      <div className="flex gap-2 pt-1">
                        <button
                          onClick={() => setConfirmDeleteItemId(null)}
                          className="flex-1 px-3 py-1.5 text-sm rounded-md border border-gray-300 text-gray-600 hover:bg-gray-50 transition-colors"
                        >
                          Anuluj
                        </button>
                        <button
                          disabled={deleteItemMutation.isPending}
                          onClick={() => {
                            deleteItemMutation.mutate(confirmDeleteItemId, {
                              onSuccess: () => setConfirmDeleteItemId(null),
                            });
                          }}
                          className="flex-1 px-3 py-1.5 text-sm rounded-md bg-red-600 text-white font-medium hover:bg-red-700 transition-colors disabled:opacity-50"
                        >
                          {deleteItemMutation.isPending ? "Usuwanie…" : "Usuń"}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })()}

            </>
          ) : (
            /* Editable — assign categories (and optionally edit OCR fields) */
            <>
              {/* Top-level OCR fields — always editable */}
              <div className="rounded-xl border border-gray-200 p-4 space-y-2">
                <label className="block text-xs text-gray-600">
                  Sklep
                  <input
                    type="text"
                    value={editedVendor}
                    onChange={(e) => setEditedVendor(e.target.value)}
                    className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </label>
                <div className="block text-xs text-gray-600">
                  Normalizuj jako
                  <VendorDropdown
                    value={editedNormalizedVendor}
                    onChange={setEditedNormalizedVendor}
                  />
                </div>
                <label className="block text-xs text-gray-600">
                  Data
                  <DateInput
                    value={editedDate}
                    onChange={setEditedDate}
                    inputSize="sm"
                    className="mt-1 w-full"
                  />
                </label>
                <div className="block text-xs text-gray-600">
                  Suma (PLN)
                  <div className="flex flex-col gap-1.5 mt-1">
                    <div>
                      <p className="text-[10px] text-gray-400 mb-0.5">Z paragonu (edytowalna)</p>
                      <input
                        type="text"
                        inputMode="decimal"
                        value={editedTotal}
                        onChange={(e) => setEditedTotal(e.target.value)}
                        className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                      />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-[10px] text-gray-400">Z produktów (wyliczona)</p>
                        {totalsMatch ? (
                          <span
                            className="inline-flex items-center gap-1 text-[10px] font-semibold text-green-700 bg-green-100 px-1.5 py-0.5 rounded-full"
                            title="Sumy się zgadzają"
                          >
                            ✓ zgodne
                          </span>
                        ) : (
                          <span
                            className="inline-flex items-center gap-1 text-[10px] font-semibold text-red-600 bg-red-100 px-1.5 py-0.5 rounded-full"
                            title="Sumy się nie zgadzają"
                          >
                            ✗ różnica {parsedTotal - calculatedTotal > 0 ? "+" : ""}{(parsedTotal - calculatedTotal).toFixed(2)} PLN
                          </span>
                        )}
                      </div>
                      <div className="w-full text-sm border border-gray-100 bg-gray-50 rounded-md px-2 py-1 text-gray-700 select-none">
                        {calculatedTotal.toFixed(2)}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Tags section (editable view) */}
              <div className="rounded-xl border border-gray-200 p-4 space-y-2">
                <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">Tagi</h2>
                <TagsEditor
                  tags={scan.tags ?? []}
                  onChange={(tags) => tagsMutation.mutate(tags)}
                  allTags={allTags}
                />
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
                className="w-full py-2.5 rounded-md bg-accent text-white font-medium text-sm hover:bg-accent-hover disabled:opacity-50 transition-colors"
              >
                {confirmMutation.isPending ? "Zapisywanie…" : "Potwierdź paragon"}
              </button>

              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide">
                    Przypisz kategorie
                  </h2>
                  {productSearch && (
                    <span className="text-xs text-gray-400">
                      {products.filter((p) =>
                        p.name.toLowerCase().includes(productSearch.toLowerCase()) ||
                        (editedNormalizedProducts[p.name] ?? "").toLowerCase().includes(productSearch.toLowerCase())
                      ).length}{" / "}{products.length}
                    </span>
                  )}
                </div>
                {products.length > 5 && (
                  <input
                    type="search"
                    value={productSearch}
                    onChange={(e) => setProductSearch(e.target.value)}
                    placeholder="Szukaj produktu…"
                    className="w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                )}
                {products
                  .map((product, index) => ({ product, index }))
                  .filter(({ product }) =>
                    !productSearch ||
                    product.name.toLowerCase().includes(productSearch.toLowerCase()) ||
                    (editedNormalizedProducts[product.name] ?? "").toLowerCase().includes(productSearch.toLowerCase())
                  )
                  .map(({ product, index }) => (
                  <div key={index} className="rounded-lg border border-gray-200 bg-white">
                    {/* Product name + price — always visible at the top */}
                    <div className="px-3 pt-3 pb-2 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <input
                          type="text"
                          value={product.name}
                          onChange={(e) => updateEditedProduct(index, { name: e.target.value })}
                          placeholder="Nazwa produktu"
                          className="flex-1 text-sm font-medium text-gray-900 border border-gray-200 rounded-md px-2 py-0.5 focus:outline-none focus:ring-2 focus:ring-accent min-w-0"
                        />
                        <div className="relative shrink-0 ml-2" ref={openMenuIndex === index ? menuRef : undefined}>
                          <button
                            type="button"
                            onClick={() => setOpenMenuIndex(openMenuIndex === index ? null : index)}
                            className="p-1 rounded text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors leading-none"
                            title="Opcje"
                          >
                            ⋯
                          </button>
                          {openMenuIndex === index && (
                            <div className="absolute right-0 top-full mt-1 z-50 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[130px]">
                              <button
                                type="button"
                                onClick={() => { removeProduct(index); setOpenMenuIndex(null); }}
                                className="w-full text-left px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                              >
                                Usuń produkt
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {product.quantity} × {(product.unit_price ?? product.price).toFixed(2)} PLN
                      </p>
                    </div>

                    {/* Numeric field editors */}
                    <div className="flex gap-2 px-3 pb-2 border-t border-gray-100">
                        <label className="flex-1 text-xs text-gray-600 pt-2">
                          Ilość
                          <input
                            type="number"
                            step="0.001"
                            value={product.quantity}
                            onChange={(e) =>
                              updateEditedProduct(index, {
                                quantity: parseFloat(e.target.value) || 0,
                              })
                            }
                            className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                          />
                        </label>
                        <label className="flex-1 text-xs text-gray-600 pt-2">
                          Cena jedn.
                          <input
                            type="text"
                            inputMode="decimal"
                            value={priceInputs[index]?.unit ?? ""}
                            onChange={(e) => updatePriceInput(index, "unit", e.target.value)}
                            className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                          />
                        </label>
                        <label className="flex-1 text-xs text-gray-600 pt-2">
                          Cena łączna
                          <input
                            type="text"
                            inputMode="decimal"
                            value={priceInputs[index]?.total ?? ""}
                            onChange={(e) => updatePriceInput(index, "total", e.target.value)}
                            className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:ring-2 focus:ring-accent"
                          />
                        </label>
                      </div>

                    {/* Normalized product name */}
                    <div className="px-3 pb-2 border-t border-gray-100">
                      <div className="block text-xs text-gray-600 pt-2">
                        Normalizuj jako
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
                type="button"
                onClick={addProduct}
                className="w-full py-2 rounded-md border border-dashed border-gray-300 text-sm text-gray-500 hover:border-accent hover:text-accent transition-colors"
              >
                + Dodaj produkt
              </button>

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
                className="mt-2 w-full py-2.5 rounded-md bg-accent text-white font-medium text-sm hover:bg-accent-hover disabled:opacity-50 transition-colors"
              >
                {confirmMutation.isPending ? "Zapisywanie…" : "Potwierdź paragon"}
              </button>

              {confirmMutation.isError && (
                <p className="text-sm text-red-500 text-center">
                  Błąd zapisu. Spróbuj ponownie.
                </p>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
