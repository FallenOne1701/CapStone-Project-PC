const TONES: Record<string, string> = {
  drafted:
    "bg-secondary-container text-on-secondary-container border-transparent",
  approved:
    "bg-emerald-50 text-emerald-800 border-emerald-200",
  active:
    "bg-emerald-50 text-emerald-800 border-emerald-200",
  pending:
    "bg-surface-container text-on-surface-variant border-transparent",
  pending_approval:
    "bg-amber-50 text-amber-900 border-amber-200",
  rejected:
    "bg-error-container text-on-error-container border-transparent",
  not_covered:
    "bg-surface-variant text-on-surface-variant border-transparent",
  inactive:
    "bg-surface-container text-on-surface-variant border-transparent",
};

export function StatusBadge({
  status,
  className = "",
}: {
  status: string;
  className?: string;
}) {
  const tone = TONES[status] ?? TONES.pending;
  return (
    <span
      className={`inline-flex items-center rounded px-2 py-0.5 font-label-sm text-label-sm uppercase font-semibold border ${tone} ${className}`}
    >
      {status.replace(/_/g, " ")}
    </span>
  );
}
