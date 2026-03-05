"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getGroundTruth, updateGroundTruth } from "@/lib/api";
import { TransactionModel } from "@/lib/types";
import Link from "next/link";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";

function ReceiptImage({ entryId }: { entryId: number }) {
  const [error, setError] = useState(false);
  const [loaded, setLoaded] = useState(false);

  if (error) {
    return (
      <div className="flex items-center justify-center rounded-xl border border-dashed border-gray-300 bg-gray-50 h-64 text-gray-400 text-sm">
        Obraz niedostępny
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden bg-gray-50">
      {!loaded && (
        <div className="flex items-center justify-center h-64">
          <svg
            className="animate-spin h-8 w-8 text-accent"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
            />
          </svg>
        </div>
      )}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={`/api/ground-truth/${entryId}/image`}
        alt={`Ground truth ${entryId}`}
        className={`w-full object-contain max-h-[70vh] ${loaded ? "" : "hidden"}`}
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
      />
    </div>
  );
}

export default function GroundTruthEditPage({
  params,
}: {
  params: { id: string };
}) {
  const entryId = Number(params.id);
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: entry, isLoading } = useQuery({
    queryKey: ["ground-truth", entryId],
    queryFn: () => getGroundTruth(entryId),
  });

  const [form, setForm] = useState<string>("");

  useEffect(() => {
    if (entry) {
      setForm(JSON.stringify(entry.ground_truth, null, 2));
    }
  }, [entry]);

  const saveMutation = useMutation({
    mutationFn: (gt: TransactionModel) => updateGroundTruth(entryId, gt),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ground-truth"] });
      router.push("/ground-truth");
    },
  });

  const [parseError, setParseError] = useState<string | null>(null);

  function handleSave() {
    setParseError(null);
    let parsed: TransactionModel;
    try {
      parsed = JSON.parse(form);
    } catch {
      setParseError("Nieprawidłowy JSON – popraw przed zapisem.");
      return;
    }
    saveMutation.mutate(parsed);
  }

  if (isLoading) {
    return (
      <div className="text-sm text-gray-400 py-16 text-center">Ładowanie…</div>
    );
  }

  if (!entry) {
    return (
      <div className="text-sm text-red-500 py-16 text-center">
        Nie znaleziono wpisu.{" "}
        <Link href="/ground-truth" className="underline">
          Wróć
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link
          href="/ground-truth"
          className="text-sm text-gray-500 hover:text-gray-700"
        >
          ← Dane wzorcowe
        </Link>
        <h1 className="text-xl font-bold text-gray-900 flex-1 truncate">
          {entry.filename}
        </h1>
      </div>

      <div className="flex gap-6 items-start">
        {/* Receipt image */}
        <div className="w-80 shrink-0">
          <ReceiptImage entryId={entryId} />
        </div>

        {/* JSON editor */}
        <div className="flex-1 space-y-2 min-w-0">
          <label className="text-sm font-medium text-gray-700">
            JSON transakcji
          </label>
          <p className="text-xs text-gray-400">
            Edytuj dane wzorcowe bezpośrednio. Musi być poprawny JSON zgodny ze schematem TransactionModel.
          </p>
          <textarea
            value={form}
            onChange={(e) => setForm(e.target.value)}
            rows={24}
            spellCheck={false}
            className="w-full rounded-md border border-gray-200 px-3 py-2 font-mono text-xs text-gray-800 focus:outline-none focus:ring-2 focus:ring-accent resize-y"
          />
          {parseError && (
            <p className="text-sm text-red-500">{parseError}</p>
          )}
          {saveMutation.isError && (
            <p className="text-sm text-red-500">
              Zapis nieudany. Sprawdź dane i spróbuj ponownie.
            </p>
          )}
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="px-5 py-2.5 rounded-md bg-accent text-white font-medium text-sm hover:bg-accent-hover disabled:opacity-50 transition-colors"
          >
            {saveMutation.isPending ? "Zapisywanie…" : "Zapisz zmiany"}
          </button>
        </div>
      </div>
    </div>
  );
}
