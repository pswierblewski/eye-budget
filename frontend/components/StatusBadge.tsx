const STATUS_STYLES: Record<string, string> = {
  new: "bg-gray-100 text-gray-600",
  pending: "bg-gray-100 text-gray-600",
  processing: "bg-blue-100 text-blue-700",
  processed: "bg-yellow-100 text-yellow-700",
  to_confirm: "bg-orange-100 text-orange-700",
  done: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
};

const STATUS_LABELS: Record<string, string> = {
  new: "Nowy",
  pending: "Oczekujący",
  processing: "Przetwarzanie",
  processed: "Przetworzony",
  to_confirm: "Do potwierdzenia",
  done: "Gotowe",
  failed: "Błąd",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-500";
  const label = STATUS_LABELS[status] ?? status;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${style}`}
    >
      {label}
    </span>
  );
}
