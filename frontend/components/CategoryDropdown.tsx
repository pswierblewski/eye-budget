"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listCategories, listCategoryGroups, createCategory } from "@/lib/api";
import { CategoryItem } from "@/lib/types";

type CategoryCandidate = {
  category_id: number;
  category_name: string;
  category_score: number;
};

interface CategoryDropdownProps {
  value: number | undefined;
  onChange: (id: number) => void;
  candidates?: CategoryCandidate[];
}

function breadcrumb(c: CategoryItem): string {
  return [c.group_name, c.parent_name, c.name].filter(Boolean).join(" / ");
}

export function CategoryDropdown({
  value,
  onChange,
  candidates = [],
}: CategoryDropdownProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newGroup, setNewGroup] = useState("");
  const [newParentId, setNewParentId] = useState<number | "">("");

  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const { data: allCategories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: listCategories,
    enabled: open,
  });

  const { data: groups = [] } = useQuery({
    queryKey: ["category-groups"],
    queryFn: listCategoryGroups,
    enabled: showCreate,
  });

  const addMutation = useMutation({
    mutationFn: ({
      name,
      group_name,
      parent_id,
    }: {
      name: string;
      group_name: string;
      parent_id: number | null;
    }) => createCategory(name, group_name, parent_id),
    onSuccess: (cat) => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      queryClient.invalidateQueries({ queryKey: ["category-groups"] });
      onChange(cat.id);
      setOpen(false);
      setSearch("");
      setShowCreate(false);
      setNewName("");
      setNewGroup("");
      setNewParentId("");
    },
  });

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    function handleMouseDown(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
        setSearch("");
        setShowCreate(false);
      }
    }
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [open]);

  useEffect(() => {
    if (open && !showCreate) {
      setTimeout(() => searchRef.current?.focus(), 0);
    }
  }, [open, showCreate]);

  const currentCategory = allCategories.find((c) => c.id === value);
  const currentLabel = currentCategory ? breadcrumb(currentCategory) : undefined;

  // Sorted candidates
  const sortedCandidates = [...candidates].sort(
    (a, b) => b.category_score - a.category_score
  );
  const candidateIds = new Set(sortedCandidates.map((c) => c.category_id));

  const searchLower = search.toLowerCase();

  const filteredCandidates = sortedCandidates.filter(
    (c) => !search || c.category_name.toLowerCase().includes(searchLower)
  );

  const filteredAll = allCategories
    .filter((c) => !candidateIds.has(c.id))
    .filter(
      (c) => !search || breadcrumb(c).toLowerCase().includes(searchLower)
    );

  const hasResults = filteredCandidates.length > 0 || filteredAll.length > 0;

  // Parent-level categories (no parent themselves) for the create form
  const parentLevelCategories = allCategories.filter(
    (c) => c.parent_name === null
  );

  const handleSubmitCreate = () => {
    if (!newName.trim() || !newGroup.trim()) return;
    addMutation.mutate({
      name: newName.trim(),
      group_name: newGroup.trim(),
      parent_id: newParentId !== "" ? Number(newParentId) : null,
    });
  };

  return (
    <div
      ref={containerRef}
      className="relative mt-1"
      onClick={(e) => e.stopPropagation()}
    >
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="w-full text-left text-sm border border-indigo-200 rounded-md px-2 py-1
          bg-indigo-50 focus:outline-none focus:ring-2 focus:ring-[#635bff]
          text-gray-900"
      >
        {currentLabel ?? <span className="text-gray-400">Wybierz kategorię…</span>}
      </button>

      {open && (
        <div
          className="absolute z-50 mt-1 w-full min-w-[280px] bg-white border border-gray-200
            rounded-lg shadow-lg overflow-hidden"
        >
          {!showCreate ? (
            <>
              {/* Search */}
              <div className="flex items-center gap-1 p-2 border-b border-gray-100">
                <input
                  ref={searchRef}
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Escape") {
                      setOpen(false);
                      setSearch("");
                    }
                  }}
                  placeholder="Szukaj kategorii…"
                  className="flex-1 text-sm border border-gray-200 rounded-md px-2 py-1
                    focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                />
              </div>

              <ul className="max-h-64 overflow-y-auto py-1">
                {/* AI suggestions section */}
                {filteredCandidates.length > 0 && (
                  <>
                    <li className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-[#635bff] bg-indigo-50 sticky top-0">
                      Propozycje AI
                    </li>
                    {filteredCandidates.map((c) => {
                      const cat = allCategories.find(
                        (a) => a.id === c.category_id
                      );
                      const full = cat ? breadcrumb(cat) : c.category_name;
                      return (
                        <li key={c.category_id}>
                          <button
                            type="button"
                            onClick={() => {
                              onChange(c.category_id);
                              setOpen(false);
                              setSearch("");
                            }}
                            className={`w-full text-left px-3 py-1.5 text-sm hover:bg-indigo-50
                              transition-colors flex items-center justify-between gap-2
                              ${value === c.category_id ? "font-semibold text-[#635bff]" : "text-gray-800"}`}
                          >
                            <span>{full}</span>
                            <span className="text-[10px] text-gray-400 shrink-0">
                              {Math.round(c.category_score * 100)}%
                            </span>
                          </button>
                        </li>
                      );
                    })}
                    {filteredAll.length > 0 && (
                      <li className="px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400 bg-gray-50 sticky top-6">
                        Wszystkie kategorie
                      </li>
                    )}
                  </>
                )}

                {/* All categories */}
                {filteredAll.map((c) => {
                  const prefix = [c.group_name, c.parent_name]
                    .filter(Boolean)
                    .join(" / ");
                  return (
                    <li key={c.id}>
                      <button
                        type="button"
                        onClick={() => {
                          onChange(c.id);
                          setOpen(false);
                          setSearch("");
                        }}
                        className={`w-full text-left px-3 py-1.5 text-sm hover:bg-indigo-50
                          transition-colors
                          ${value === c.id ? "font-semibold text-[#635bff]" : "text-gray-800"}`}
                      >
                        {prefix && (
                          <span className="text-gray-400">{prefix} / </span>
                        )}
                        <span>{c.name}</span>
                      </button>
                    </li>
                  );
                })}

                {!hasResults && (
                  <li className="px-3 py-2 text-xs text-gray-400">
                    {search.trim()
                      ? `Brak wyników dla „${search.trim()}"`
                      : "Brak kategorii"}
                  </li>
                )}
              </ul>

              {/* Add new */}
              <div className="border-t border-gray-100 p-2">
                <button
                  type="button"
                  onClick={() => {
                    setNewName(search.trim());
                    setShowCreate(true);
                  }}
                  className="w-full text-xs text-[#635bff] hover:text-[#4f46e5] text-left
                    py-1 px-1 hover:bg-indigo-50 rounded transition-colors"
                >
                  + Nowa kategoria{search.trim() ? ` „${search.trim()}"` : ""}
                </button>
              </div>
            </>
          ) : (
            /* Inline create form */
            <div className="p-3 space-y-2">
              <p className="text-xs font-semibold text-gray-700">
                Nowa kategoria
              </p>

              <label className="block text-xs text-gray-600">
                Nazwa
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  autoFocus
                  className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1
                    focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                />
              </label>

              <label className="block text-xs text-gray-600">
                Grupa
                <input
                  list="cat-groups"
                  type="text"
                  value={newGroup}
                  onChange={(e) => setNewGroup(e.target.value)}
                  placeholder="e.g. Żywność"
                  className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1
                    focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                />
                <datalist id="cat-groups">
                  {groups.map((g) => (
                    <option key={g} value={g} />
                  ))}
                </datalist>
              </label>

              <label className="block text-xs text-gray-600">
                Nadrzędna (opcjonalnie)
                <select
                  value={newParentId}
                  onChange={(e) =>
                    setNewParentId(
                      e.target.value === "" ? "" : Number(e.target.value)
                    )
                  }
                  className="mt-1 w-full text-sm border border-gray-200 rounded-md px-2 py-1
                    focus:outline-none focus:ring-2 focus:ring-[#635bff]"
                >
                  <option value="">Brak</option>
                  {parentLevelCategories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.group_name ? `${c.group_name} / ` : ""}
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>

              <div className="flex gap-2 pt-1">
                <button
                  type="button"
                  disabled={
                    !newName.trim() ||
                    !newGroup.trim() ||
                    addMutation.isPending
                  }
                  onClick={handleSubmitCreate}
                  className="flex-1 text-xs font-medium py-1.5 px-3 rounded-md bg-[#635bff]
                    text-white disabled:opacity-40 disabled:cursor-not-allowed
                    hover:bg-[#4f46e5] transition-colors"
                >
                  {addMutation.isPending ? "Dodawanie…" : "Dodaj"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  className="flex-1 text-xs font-medium py-1.5 px-3 rounded-md border
                    border-gray-200 hover:bg-gray-50 text-gray-600 transition-colors"
                >
                  Anuluj
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
