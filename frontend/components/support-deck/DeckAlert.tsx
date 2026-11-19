export function DeckAlert({
  tone = "error",
  children,
}: {
  tone?: "error" | "warn" | "ok";
  children: React.ReactNode;
}) {
  const styles =
    tone === "ok"
      ? "bg-secondary-container/70 text-on-secondary-container"
      : tone === "warn"
        ? "bg-amber-50 text-amber-900 border border-amber-200"
        : "bg-error-container text-on-error-container";
  return (
    <div className={`rounded-xl px-3.5 py-3 text-body-md font-body-md ${styles}`}>
      {children}
    </div>
  );
}
