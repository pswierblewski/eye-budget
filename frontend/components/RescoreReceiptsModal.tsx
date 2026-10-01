"use client";

import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Button, Modal } from "@/components/ui";
import { MutationErrorNotice } from "@/components/QueryState";
import { rescorePendingReceipts } from "@/lib/api";
import { getPusher } from "@/lib/pusher";
import type { RescoreReport } from "@/lib/types";

type Phase = "idle" | "running" | "report" | "done" | "error";

export function RescoreReceiptsModal({
  open,
  onClose,
  onFinished,
}: {
  open: boolean;
  onClose: () => void;
  onFinished: () => void;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState<{ index: number; total: number } | null>(null);
  const [report, setReport] = useState<RescoreReport | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const channelRef = useRef<ReturnType<ReturnType<typeof getPusher>["subscribe"]> | null>(null);

  useEffect(() => {
    return () => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
    };
  }, []);

  const mutation = useMutation({
    mutationFn: (dryRun: boolean) => rescorePendingReceipts(dryRun),
    onMutate: () => {
      setPhase("running");
      setProgress(null);
      setErrorMsg(null);
    },
    onSuccess: ({ task_id }) => {
      channelRef.current?.unbind_all();
      channelRef.current?.unsubscribe();
      const channel = getPusher().subscribe("receipts");
      channelRef.current = channel;
      channel.bind("receipt.rescore_progress", (data: { task_id: string; index: number; total: number }) => {
        if (data.task_id !== task_id) return;
        setProgress({ index: data.index, total: data.total });
      });
      channel.bind("receipt.rescore_done", (data: { task_id: string; report: RescoreReport }) => {
        if (data.task_id !== task_id) return;
        setReport(data.report);
        setPhase(data.report.dry_run ? "report" : "done");
        if (!data.report.dry_run) onFinished();
        channel.unbind_all();
        channel.unsubscribe();
      });
      channel.bind("receipt.rescore_error", (data: { task_id: string; error: string }) => {
        if (data.task_id !== task_id) return;
        setErrorMsg(data.error);
        setPhase("error");
        channel.unbind_all();
        channel.unsubscribe();
      });
    },
    onError: () => setPhase("idle"),
  });

  const close = () => {
    if (phase === "running") return;
    setPhase("idle");
    setReport(null);
    onClose();
  };

  return (
    <Modal open={open} onClose={close} maxWidth="lg">
      <div className="p-6 flex flex-col gap-4 text-sm">
        <h2 className="text-lg font-semibold text-gray-900">Potwierdź automatycznie — oczekujące paragony</h2>
        <MutationErrorNotice mutation={mutation} />

        {phase === "idle" && (
          <p className="text-gray-600">
            Dla paragonów „Do potwierdzenia” ponownie uruchomimy kategoryzację i bramkę auto-potwierdzenia.
            Najpierw zobaczysz raport — nic nie zostanie potwierdzone bez Twojej zgody.
          </p>
        )}

        {phase === "running" && (
          <p className="text-gray-600">
            {progress ? `Sprawdzanie ${progress.index} / ${progress.total}…` : "Uruchamianie…"}
          </p>
        )}

        {phase === "report" && report && (
          <div className="flex flex-col gap-2">
            <p className="font-medium text-gray-900">
              {report.eligible} z {report.total} paragonów potwierdziłoby się automatycznie.
            </p>
            {report.top_reasons.length > 0 && (
              <>
                <p className="text-gray-500">Najczęstsze blokady:</p>
                <ul className="list-disc pl-5 text-gray-700 space-y-1">
                  {report.top_reasons.map((r) => (
                    <li key={r.code}>{`${r.message} — ${r.count}×`}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        {phase === "done" && report && (
          <p className="font-medium text-green-700">Potwierdzono automatycznie {report.confirmed} paragonów.</p>
        )}

        {phase === "error" && (
          <p className="text-red-600">Auto-potwierdzenie nie powiodło się: {errorMsg}</p>
        )}

        <div className="flex justify-end gap-2">
          <Button variant="secondary" onClick={close} disabled={phase === "running"}>
            Zamknij
          </Button>
          {phase === "idle" && (
            <Button onClick={() => mutation.mutate(true)} disabled={mutation.isPending}>
              Sprawdź auto-potwierdzenie
            </Button>
          )}
          {phase === "report" && report && report.eligible > 0 && (
            <Button onClick={() => mutation.mutate(false)} disabled={mutation.isPending}>
              {`Potwierdź automatycznie ${report.eligible}`}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}
