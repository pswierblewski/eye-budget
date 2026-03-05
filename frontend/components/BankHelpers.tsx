// CandidateBar – score visualization for receipt-linking candidates

export function CandidateBar({
  name,
  score,
}: {
  name: string;
  score: number;
}) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-48 truncate text-gray-600" title={name}>
        {name}
      </span>
      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
        <div
          className="h-2 rounded-full bg-accent"
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-10 text-right text-gray-500">{pct}%</span>
    </div>
  );
}

