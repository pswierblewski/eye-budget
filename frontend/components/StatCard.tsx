export function StatCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-6 flex flex-col gap-1 ${
        accent
          ? "border-[#635bff] bg-[#635bff]/5"
          : "border-gray-200 bg-white"
      }`}
    >
      <span className="text-sm font-medium text-gray-500">{label}</span>
      <span
        className={`text-3xl font-bold ${accent ? "text-[#635bff]" : "text-gray-900"}`}
      >
        {value}
      </span>
    </div>
  );
}
