"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listVendors, createVendor } from "@/lib/api";

interface VendorDropdownProps {
  value: string;
  onChange: (name: string) => void;
}

export function VendorDropdown({ value, onChange }: VendorDropdownProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data: vendors = [] } = useQuery({
    queryKey: ["vendors"],
    queryFn: listVendors,
    enabled: open,
  });

  const addMutation = useMutation({
    mutationFn: (name: string) => createVendor(name),
    onSuccess: (vendor) => {
      queryClient.invalidateQueries({ queryKey: ["vendors"] });
      onChange(vendor.name);
      setOpen(false);
      setSearch("");
    },
  });

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setSearch("");
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [open]);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (open) {
      setTimeout(() => searchRef.current?.focus(), 0);
    }
  }, [open]);

  const filtered = vendors.filter((v) =>
    v.name.toLowerCase().includes(search.toLowerCase())
  );

  const handleSelect = (name: string) => {
    onChange(name);
    setOpen(false);
    setSearch("");
  };

  const handleAdd = () => {
    const trimmed = search.trim();
    if (!trimmed) return;
    // If exact match already exists, just select it
    const existing = vendors.find(
      (v) => v.name.toLowerCase() === trimmed.toLowerCase()
    );
    if (existing) {
      handleSelect(existing.name);
      return;
    }
    addMutation.mutate(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      if (filtered.length === 1) {
        handleSelect(filtered[0].name);
      } else if (filtered.length === 0 && search.trim()) {
        handleAdd();
      }
    } else if (e.key === "Escape") {
      setOpen(false);
      setSearch("");
    }
  };

  return (
    <div ref={containerRef} className="relative mt-1" onClick={(e) => e.stopPropagation()}>
      {/* Trigger button — styled to match the old indigo input */}
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full text-left text-sm border border-indigo-200 rounded-md px-2 py-1
          bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-[#635bff]
          text-gray-900 truncate"
      >
        {value || <span className="text-gray-400">np. Biedronka</span>}
      </button>

      {open && (
        <div
          className="absolute z-50 mt-1 w-full bg-white border border-gray-200
            rounded-lg shadow-lg overflow-hidden"
        >
          {/* Search + Add row */}
          <div className="flex items-center gap-1 p-2 border-b border-gray-100">
            <input
              ref={searchRef}
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Szukaj dostawców…"
              className="flex-1 text-sm border border-gray-200 rounded-md px-2 py-1
                focus:outline-none focus:ring-2 focus:ring-[#635bff]"
            />
            <button
              type="button"
              disabled={!search.trim() || addMutation.isPending}
              onClick={handleAdd}
              className="shrink-0 text-xs font-medium px-2 py-1 rounded-md
                bg-[#635bff] text-white disabled:opacity-40 disabled:cursor-not-allowed
                hover:bg-[#4f46e5] transition-colors"
            >
              {addMutation.isPending ? "Dodawanie…" : "Dodaj"}
            </button>
          </div>

          {/* Vendor list */}
          <ul className="max-h-52 overflow-y-auto py-1">
            {filtered.length === 0 ? (
              <li className="px-3 py-2 text-xs text-gray-400">
                {search.trim()
                  ? `Brak wyników — kliknij Dodaj, aby utworzyć „${search.trim()}"`
                  : "Brak dostawców"}
              </li>
            ) : (
              filtered.map((v) => (
                <li key={v.id}>
                  <button
                    type="button"
                    onClick={() => handleSelect(v.name)}
                    className={`w-full text-left px-3 py-1.5 text-sm hover:bg-indigo-50
                      transition-colors ${v.name === value ? "font-semibold text-[#635bff]" : "text-gray-800"}`}
                  >
                    {v.name}
                  </button>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
