"use client";

import { useState } from "react";
import { useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getSettlementGroup, updateSettlementGroup, deleteSettlementGroup } from "@/lib/api";
import { formatAmount } from "@/components/ui/Amount";
import {
  PageHeader,
  NavLink,
  Button,
  Card,
  SectionLabel,
  Input,
  ConfirmDeleteModal,
} from "@/components/ui";
import { SettlementGroupBadge } from "@/components/SettlementGroupBadge";

export default function SettlementGroupDetailPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const router = useRouter();
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState("");
  const [note, setNote] = useState("");
  const [deleteOpen, setDeleteOpen] = useState(false);

  const { data: g, isLoading } = useQuery({
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
    if (!g) return;
    if (!editing) {
      setTitle(g.title ?? "");
      setNote(g.note ?? "");
    }
  }, [g, editing]);

  if (isLoading) {
    return <div className="p-8 text-gray-400 text-sm">Ładowanie…</div>;
  }
  if (!g) {
    return (
      <div className="p-8 text-center text-sm text-gray-500">
        Nie znaleziono grupy.
        <Link href="/settlement-groups" className="block mt-2 text-violet-600">
          ← Lista
        </Link>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col gap-4 pb-8">
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
          <div className="flex gap-2">
            {editing ? (
              <>
                <Button variant="secondary" onClick={() => setEditing(false)}>
                  Anuluj
                </Button>
                <Button
                  variant="primary"
                  disabled={saveMutation.isPending}
                  onClick={() => saveMutation.mutate()}
                >
                  Zapisz
                </Button>
              </>
            ) : (
              <Button
                variant="secondary"
                onClick={() => {
                  setTitle(g.title ?? "");
                  setNote(g.note ?? "");
                  setEditing(true);
                }}
              >
                Edytuj
              </Button>
            )}
            <Button variant="danger" onClick={() => setDeleteOpen(true)}>
              Usuń grupę
            </Button>
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
        <ul className="divide-y">
          {g.members.map((m) => (
            <li key={`${m.source_type}-${m.id}`} className="py-2 flex flex-wrap justify-between gap-2 text-sm">
              <Link
                href={m.source_type === "bank" ? `/bank-transactions/${m.id}` : `/cash-transactions/${m.id}`}
                className="text-violet-600 hover:underline"
              >
                {m.source_type === "bank" ? "Bank" : "Gotówka"} #{m.id}
                {m.description || m.vendor_name
                  ? ` — ${m.vendor_name ?? m.description ?? ""}`
                  : ""}
              </Link>
              <span className="text-gray-500 text-xs">
                {m.booking_date} · {formatAmount(m.amount, m.currency || "PLN")}
              </span>
            </li>
          ))}
        </ul>
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
  );
}
