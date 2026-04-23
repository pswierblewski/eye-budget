"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { listSettlementGroups, createSettlementGroup } from "@/lib/api";
import {
  PageHeader,
  Button,
  Input,
  Card,
} from "@/components/ui";
import { SettlementGroupBadge } from "@/components/SettlementGroupBadge";
import { Modal } from "@/components/ui/Modal";
import { QueryState, MutationErrorNotice } from "@/components/QueryState";

export default function SettlementGroupsPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 30;
  const [newOpen, setNewOpen] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  const listQuery = useQuery({
    queryKey: ["settlement-groups", search, page],
    queryFn: () =>
      listSettlementGroups({
        search: search || undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize,
        sort_by: "created_at",
        sort_dir: "desc",
      }),
  });

  const createEmpty = useMutation({
    mutationFn: () =>
      createSettlementGroup({
        title: newTitle.trim() || null,
        note: null,
        members: [],
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settlement-groups"] });
      setNewOpen(false);
      setNewTitle("");
    },
  });

  return (
    <div className="h-full flex flex-col gap-4">
      <MutationErrorNotice mutation={createEmpty} />
      <PageHeader
        title="Powiązane operacje"
        variant="list"
        actions={
          <Button variant="primary" onClick={() => setNewOpen(true)}>
            Nowa pusta grupa
          </Button>
        }
      />
      <div className="flex flex-wrap gap-2 items-center">
        <Input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
          placeholder="Szukaj po tytule lub notatce…"
          className="max-w-md"
        />
      </div>
      <QueryState
        query={listQuery}
        errorTitle="Nie udało się pobrać listy grup."
        loadingFallback={<p className="text-sm text-gray-400">Ładowanie…</p>}
      >
        {(data) => {
          const total = data.total;
          const totalPages = Math.max(1, Math.ceil(total / pageSize));
          return (
            <>
              <Card padding="none" className="overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="text-left p-3">Tytuł</th>
                      <th className="text-left p-3 w-36">Utworzono</th>
                      <th className="text-right p-3 w-24">Operacje</th>
                      <th className="w-12" />
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {data.items.map((g) => (
                      <tr key={g.id} className="hover:bg-gray-50/80">
                        <td className="p-3">
                          <Link
                            href={`/settlement-groups/${g.id}`}
                            className="font-medium text-violet-700 hover:underline"
                          >
                            {g.title?.trim() || `Grupa #${g.id}`}
                          </Link>
                          {g.note && (
                            <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                              {g.note}
                            </p>
                          )}
                        </td>
                        <td className="p-3 text-xs text-gray-600 whitespace-nowrap">
                          {g.created_at.slice(0, 10)}
                        </td>
                        <td className="p-3 text-right">
                          <SettlementGroupBadge count={g.member_count} />
                        </td>
                        <td className="p-3 text-right">
                          <Link
                            href={`/settlement-groups/${g.id}`}
                            className="text-xs text-violet-600 hover:underline"
                          >
                            Otwórz
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {total === 0 && (
                  <p className="p-6 text-sm text-gray-500 text-center">
                    Brak grup. Utwórz pierwszą.
                  </p>
                )}
              </Card>
              {totalPages > 1 && (
                <div className="flex justify-center gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                  >
                    Poprzednia
                  </Button>
                  <span className="text-sm text-gray-600 self-center">
                    {page} / {totalPages}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  >
                    Następna
                  </Button>
                </div>
              )}
            </>
          );
        }}
      </QueryState>

      <Modal open={newOpen} onClose={() => setNewOpen(false)}>
        <div className="p-4 space-y-3">
          <h2 className="text-lg font-semibold">Nowa pusta grupa</h2>
          <p className="text-sm text-gray-600">
            Opcjonalny tytuł — transakcje dodasz później z poziomu operacji.
          </p>
          <Input
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Tytuł (opcjonalnie)"
          />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setNewOpen(false)}>
              Anuluj
            </Button>
            <Button
              variant="primary"
              disabled={createEmpty.isPending}
              onClick={() => createEmpty.mutate()}
            >
              Utwórz
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
