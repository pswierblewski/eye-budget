"use client";

import { useState } from "react";
import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getSettlementGroup, updateSettlementGroup, deleteSettlementGroup } from "@/lib/api";
import {
  PageHeader,
  NavLink,
  Button,
  Card,
  SectionLabel,
  Input,
  ConfirmDeleteModal,
  formatAmount,
  SourceBadge,
  Amount,
} from "@/components/ui";
import { SettlementGroupBadge } from "@/components/SettlementGroupBadge";
import { QueryState, MutationErrorNotice } from "@/components/QueryState";
import { ThreeDotsMenu } from "@/components/ui/ThreeDotsMenu";
import { isoToDisplay } from "@/lib/utils";
import type { SettlementMemberRow } from "@/lib/types";

export default function SettlementGroupDetailPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);

  const groupQuery = useQuery({
    queryKey: ["settlement-group", id],
    queryFn: () => getSettlementGroup(id),
  });

  const saveMutation = useMutation({
    mutationFn: () => updateSettlementGroup(id, { title: title || null, note: note || null }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settlement-group", id] });
      queryClient.invalidateQueries({ queryKey: ["settlement-groups"] });
      setEditing(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSettlementGroup(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settlement-groups"] });
      router.push("/settlement-groups");
    },
  });

  useEffect(() => {
    const g = groupQuery.data;
    if (!g) return;
    if (!editing) {
      setTitle(g.title ?? "");
      setNote(g.note ?? "");
    }
  }, [groupQuery.data, editing]);

  return (
    <QueryState
      query={groupQuery}
      errorTitle="Nie udało się pobrać grupy."
      loadingFallback={<div className="p-8 text-gray-400 text-sm">Ładowanie…</div>}
    >
      {(g) => (
    <div className="h-full flex flex-col gap-4 pb-8">
      <MutationErrorNotice mutation={saveMutation} />
      <MutationErrorNotice mutation={deleteMutation} />
      <ConfirmDeleteModal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onConfirm={() => deleteMutation.mutate()}
        title="Usuń grupę"
        description="Usuniemy powiązania; transakcje zostaną w bazie."
        loading={deleteMutation.isPending}
      />
      <PageHeader
        variant="detail"
        title={g.title?.trim() || `Grupa #${g.id}`}
        subtitle={
          <NavLink href="/settlement-groups" label="Powiązane operacje" variant="back" size="xs" />
        }
        actions={
          <div className="flex items-center gap-2">
            {editing ? (
              <>
                <Button variant="secondary" size="sm" onClick={() => setEditing(false)}>
                  Anuluj
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  disabled={saveMutation.isPending}
                  onClick={() => saveMutation.mutate()}
                >
                  Zapisz
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setTitle(g.title ?? "");
                    setNote(g.note ?? "");
                    setEditing(true);
                  }}
                >
                  Edytuj
                </Button>
                <ThreeDotsMenu
                  variant="inline"
                  title="Więcej akcji — grupa"
                  items={[
                    {
                      label: "Usuń całą grupę…",
                      variant: "danger",
                      onClick: () => setDeleteOpen(true),
                    },
                  ]}
                />
              </>
            )}
          </div>
        }
      />
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600">Operacje w zestawie:</span>
        <SettlementGroupBadge count={g.member_count} />
      </div>
      {editing ? (
        <Card padding="md" className="space-y-2">
          <SectionLabel>Metadane</SectionLabel>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Tytuł" />
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Notatka"
            className="w-full border rounded-md p-2 text-sm min-h-[80px]"
          />
        </Card>
      ) : (
        g.note && (
          <p className="text-sm text-gray-600 max-w-2xl">{g.note}</p>
        )
      )}
      <Card padding="md" className="space-y-2">
        <SectionLabel>Bilans (informacyjnie)</SectionLabel>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm text-gray-800">
          <div>
            <div className="text-xs text-gray-500">Suma wydatków</div>
            <div className="font-semibold tabular-nums">
              {formatAmount(-Number(g.total_expense), "PLN")}
            </div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Suma wpływów</div>
            <div className="font-semibold tabular-nums">{formatAmount(g.total_income, "PLN")}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500">Netto</div>
            <div className="font-semibold tabular-nums">{formatAmount(g.net, "PLN")}</div>
          </div>
        </div>
      </Card>
      <Card padding="md" className="space-y-2">
        <SectionLabel>Operacje w zestawie</SectionLabel>
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[520px]">
            <thead>
              <tr className="text-left text-xs text-gray-500 border-b border-gray-100">
                <th className="py-2 pr-3 w-20">Źródło</th>
                <th className="py-2 pr-3 w-32">Data</th>
                <th className="py-2 pr-3">Opis</th>
                <th className="py-2 text-right w-32">Kwota</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {g.members.map((m: SettlementMemberRow) => (
                <tr key={`${m.source_type}-${m.id}`}>
                  <td className="py-2 pr-3 align-middle">
                    <SourceBadge source={m.source_type} />
                  </td>
                  <td className="py-2 pr-3 font-mono text-xs text-gray-700 whitespace-nowrap">
                    {isoToDisplay(m.booking_date)}
                  </td>
                  <td className="py-2 pr-3 align-middle">
                    <Link
                      href={m.source_type === "bank" ? `/bank-transactions/${m.id}` : `/cash-transactions/${m.id}`}
                      className="text-violet-600 hover:underline"
                    >
                      {m.vendor_name?.trim() || m.description?.trim() || "—"}
                    </Link>
                  </td>
                  <td className="py-2 text-right align-middle tabular-nums">
                    <Amount value={m.amount} currency={m.currency || "PLN"} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      {g.linked_receipts.length > 0 && (
        <Card padding="md" className="space-y-2">
          <SectionLabel>Paragony (z linków do operacji)</SectionLabel>
          <ul className="list-disc pl-4 text-sm">
            {g.linked_receipts.map((r) => (
              <li key={r.scan_id}>
                <Link href={`/receipts/${r.scan_id}`} className="text-violet-600 hover:underline">
                  {r.filename || `#${r.scan_id}`}
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      )}
    </div>
      )}
    </QueryState>
  );
}
