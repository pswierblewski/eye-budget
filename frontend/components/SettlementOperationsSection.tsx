"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getSettlementGroupByTransaction,
  addSettlementGroupMember,
  moveSettlementGroupMember,
  removeSettlementGroupMember,
  deleteSettlementGroup,
} from "@/lib/api";
import { SettlementGroupPickerModal } from "./SettlementGroupPickerModal";
import { LinkOperationsModal } from "./LinkOperationsModal";
import { formatAmount } from "@/components/ui/Amount";
import { Button, Card, SectionLabel, ConfirmDeleteModal } from "@/components/ui";
import { ThreeDotsMenu } from "@/components/ui/ThreeDotsMenu";
import { isoToDisplay } from "@/lib/utils";
import { QueryState } from "@/components/QueryState";

type Props = {
  sourceType: "bank" | "cash";
  transactionId: number;
};

const QK = {
  tx: (st: "bank" | "cash", id: number) =>
    st === "bank" ? (["bank-transaction", id] as const) : (["cash-transaction", id] as const),
  byTx: (st: "bank" | "cash", id: number) => ["settlement-group", "by-tx", st, id] as const,
  list: ["settlement-groups"] as const,
  unified: ["transactions"] as const,
  bankList: ["bank-transactions"] as const,
  cashList: ["cash-transactions"] as const,
};

export function SettlementOperationsSection({ sourceType, transactionId }: Props) {
  const queryClient = useQueryClient();
  const [linkOpen, setLinkOpen] = useState(false);
  const [pickOpen, setPickOpen] = useState(false);
  const [pickMode, setPickMode] = useState<"add" | "move">("add");
  const [deleteGroupOpen, setDeleteGroupOpen] = useState(false);

  const groupQuery = useQuery({
    queryKey: QK.byTx(sourceType, transactionId),
    queryFn: () => getSettlementGroupByTransaction(sourceType, transactionId),
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: QK.list });
    queryClient.invalidateQueries({ queryKey: QK.byTx(sourceType, transactionId) });
    queryClient.invalidateQueries({ queryKey: QK.tx(sourceType, transactionId) });
    queryClient.invalidateQueries({ queryKey: QK.unified });
    queryClient.invalidateQueries({ queryKey: QK.bankList });
    queryClient.invalidateQueries({ queryKey: QK.cashList });
  };

  const addToGroupMutation = useMutation({
    mutationFn: (groupId: number) =>
      addSettlementGroupMember(groupId, { source_type: sourceType, id: transactionId }),
    onSuccess: () => invalidateAll(),
  });

  const moveToGroupMutation = useMutation({
    mutationFn: async (newGroupId: number) => {
      const g = groupQuery.data;
      if (!g) return;
      await moveSettlementGroupMember(g.id, {
        target_group_id: newGroupId,
        source_type: sourceType,
        id: transactionId,
      });
    },
    onSuccess: () => invalidateAll(),
  });

  const removeSelfMutation = useMutation({
    mutationFn: (gId: number) => removeSettlementGroupMember(gId, sourceType, transactionId),
    onSuccess: () => invalidateAll(),
  });

  const deleteGroupMutation = useMutation({
    mutationFn: (gId: number) => deleteSettlementGroup(gId),
    onSuccess: () => invalidateAll(),
  });

  return (
    <>
      <QueryState
        query={groupQuery}
        errorTitle="Nie udało się pobrać informacji o powiązanych operacjach."
        loadingFallback={
          <Card padding="md">
            <SectionLabel>Powiązane operacje</SectionLabel>
            <p className="text-sm text-gray-400">Ładowanie…</p>
          </Card>
        }
      >
        {(group) => {
          if (!group) {
            return (
              <Card padding="md" className="space-y-3">
                <SectionLabel>Powiązane operacje</SectionLabel>
                <p className="text-sm text-gray-600">
                  Połącz tę operację z innymi, aby śledzić wspólne rozliczenie (np.
                  wydatek i zwroty).
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button variant="primary" size="sm" onClick={() => setLinkOpen(true)}>
                    Utwórz z wybranych…
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => {
                      setPickMode("add");
                      setPickOpen(true);
                    }}
                  >
                    Dołącz do istniejącej…
                  </Button>
                </div>
              </Card>
            );
          }

          const others = group.members.filter(
            (m) => !(m.source_type === sourceType && m.id === transactionId)
          );

          return (
            <Card padding="md" className="space-y-3">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <SectionLabel>Powiązane operacje</SectionLabel>
                  {group.title && (
                    <p className="text-sm font-medium text-gray-900 mt-1">
                      {group.title}
                    </p>
                  )}
                  {group.note && (
                    <p className="text-sm text-gray-600 mt-0.5">{group.note}</p>
                  )}
                </div>
                <Link
                  href={`/settlement-groups/${group.id}`}
                  className="text-sm text-violet-600 hover:underline shrink-0"
                >
                  Otwórz stronę grupy →
                </Link>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm text-gray-800">
                <div>
                  <div className="text-[11px] text-gray-500 uppercase">
                    Suma wydatków (orientacyjnie)
                  </div>
                  <div className="font-semibold tabular-nums">
                    {formatAmount(-Number(group.total_expense), "PLN")}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-gray-500 uppercase">Suma wpływów</div>
                  <div className="font-semibold tabular-nums">
                    {formatAmount(group.total_income, "PLN")}
                  </div>
                </div>
                <div>
                  <div className="text-[11px] text-gray-500 uppercase">Bilans netto</div>
                  <div className="font-semibold tabular-nums">
                    {formatAmount(group.net, "PLN")}
                  </div>
                </div>
              </div>
              {group.linked_receipts.length > 0 && (
                <div>
                  <div className="text-[11px] text-gray-500 uppercase tracking-wide mb-1">
                    Paragony w zestawie
                  </div>
                  <ul className="text-sm text-gray-700 list-disc pl-4 space-y-0.5">
                    {group.linked_receipts.map((r) => (
                      <li key={r.scan_id}>
                        <Link
                          href={`/receipts/${r.scan_id}`}
                          className="text-violet-600 hover:underline"
                        >
                          {r.filename || `Paragon #${r.scan_id}`}
                          {r.vendor_name ? ` — ${r.vendor_name}` : ""}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {others.length > 0 && (
                <div>
                  <div className="text-[11px] text-gray-500 uppercase tracking-wide mb-1">
                    Inne operacje w tym zestawie
                  </div>
                  <ul className="space-y-1.5">
                    {others.map((m) => (
                      <li
                        key={`${m.source_type}-${m.id}`}
                        className="flex flex-wrap items-baseline justify-between gap-2 text-sm text-gray-800"
                      >
                        <span>
                          {m.source_type === "bank" ? "Bank" : "Gotówka"}{" "}
                          <Link
                            href={
                              m.source_type === "bank"
                                ? `/bank-transactions/${m.id}`
                                : `/cash-transactions/${m.id}`
                            }
                            className="text-violet-600 hover:underline"
                          >
                            #{m.id}
                          </Link>
                          {m.description || m.vendor_name
                            ? ` — ${m.vendor_name ?? m.description ?? ""}`
                            : ""}
                        </span>
                        <span className="text-gray-600 whitespace-nowrap text-xs">
                          {isoToDisplay(m.booking_date)} ·{" "}
                          {formatAmount(m.amount, m.currency || "PLN")}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="flex flex-wrap items-center gap-2 pt-1">
                <ThreeDotsMenu
                  variant="inline"
                  align="left"
                  title="Więcej akcji — powiązane operacje"
                  items={[
                    {
                      label: "Przenieś do innej grupy…",
                      onClick: () => {
                        setPickMode("move");
                        setPickOpen(true);
                      },
                      disabled: moveToGroupMutation.isPending,
                    },
                    {
                      label: "Odepnij tę operację",
                      onClick: () => removeSelfMutation.mutate(group.id),
                      disabled: removeSelfMutation.isPending,
                      separator: true,
                    },
                    {
                      label: "Usuń całą grupę…",
                      onClick: () => setDeleteGroupOpen(true),
                      variant: "danger",
                    },
                  ]}
                />
              </div>
            </Card>
          );
        }}
      </QueryState>
      <LinkOperationsModal
        open={linkOpen}
        onClose={() => setLinkOpen(false)}
        current={{ source_type: sourceType, id: transactionId }}
        onCreated={() => invalidateAll()}
      />
      <SettlementGroupPickerModal
        open={pickOpen}
        onClose={() => setPickOpen(false)}
        title={pickMode === "move" ? "Wybierz docelową grupę" : "Wybierz grupę"}
        onSelect={(gid) => {
          const dg = groupQuery.data;
          if (dg === undefined) return;
          if (dg === null || pickMode === "add") {
            addToGroupMutation.mutate(gid);
            return;
          }
          if (gid === dg.id) return;
          moveToGroupMutation.mutate(gid);
        }}
      />
      <ConfirmDeleteModal
        open={deleteGroupOpen}
        onClose={() => setDeleteGroupOpen(false)}
        onConfirm={() => {
          const dg = groupQuery.data;
          if (dg && dg !== null) {
            void deleteGroupMutation
              .mutateAsync(dg.id)
              .then(() => setDeleteGroupOpen(false));
          }
        }}
        title="Usuń grupę powiązanych operacji"
        description="Powiązania zostaną usunięte. Transakcje bankowe i gotówkowe pozostaną w bazie."
        loading={deleteGroupMutation.isPending}
      />
    </>
  );
}
