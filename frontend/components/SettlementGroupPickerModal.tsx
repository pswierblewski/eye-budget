"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listSettlementGroups } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { Button, Input } from "@/components/ui";
import { SettlementGroupBadge } from "./SettlementGroupBadge";
import { QueryState } from "@/components/QueryState";

type Props = {
  open: boolean;
  onClose: () => void;
  onSelect: (groupId: number) => void;
  title?: string;
};

/**
 * Picker: existing settlement groups (same data as the directory page, compact).
 */
export function SettlementGroupPickerModal({
  open,
  onClose,
  onSelect,
  title = "Wybierz grupę",
}: Props) {
  const [search, setSearch] = useState("");
  const listQuery = useQuery({
    queryKey: ["settlement-groups", "picker", search],
    queryFn: () => listSettlementGroups({ search: search || undefined, limit: 30 }),
    enabled: open,
  });

  return (
    <Modal open={open} onClose={onClose} maxWidth="md">
      <div className="p-4 space-y-3 max-h-[70vh] flex flex-col">
        <h2 className="text-lg font-semibold text-gray-900">{title}</h2>
        <Input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Szukaj po tytule lub notatce…"
        />
        <div className="border rounded-lg overflow-y-auto min-h-0 flex-1 divide-y">
          <QueryState
            query={listQuery}
            errorTitle="Nie udało się pobrać listy grup."
            loadingFallback={
              <p className="p-3 text-sm text-gray-500">Ładowanie…</p>
            }
          >
            {(data) =>
              data.items.length === 0 ? (
                <p className="p-3 text-sm text-gray-500">Brak grup.</p>
              ) : (
                data.items.map((g) => (
                  <button
                    key={g.id}
                    type="button"
                    onClick={() => {
                      onSelect(g.id);
                      onClose();
                    }}
                    className="w-full text-left p-3 hover:bg-gray-50 flex items-center justify-between gap-2"
                  >
                    <span className="text-sm text-gray-900 truncate">
                      {g.title?.trim() || `Grupa #${g.id}`}
                    </span>
                    <SettlementGroupBadge count={g.member_count} />
                  </button>
                ))
              )
            }
          </QueryState>
        </div>
        <div className="flex justify-end">
          <Button variant="secondary" onClick={onClose}>
            Anuluj
          </Button>
        </div>
      </div>
    </Modal>
  );
}
