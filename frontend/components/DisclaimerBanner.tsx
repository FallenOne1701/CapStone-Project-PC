export function DisclaimerBanner() {
  return (
    <aside className="sticky top-16 z-30 border-b border-slate-800 bg-slate-900 px-4 py-2.5 text-slate-100 shadow-sm">
      <div className="mx-auto flex max-w-7xl items-center justify-between text-xs font-medium sm:text-[13px]">
        <div className="mx-auto flex items-center gap-2 sm:mx-0">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
          </span>
          <span className="rounded border border-slate-700 bg-slate-800 px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-emerald-400">
            Notice
          </span>
          <span className="font-semibold text-white">
            Facts-only. No investment advice.
          </span>
        </div>
        <div className="hidden items-center gap-2 text-xs text-slate-400 sm:flex">
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <span>No recommendations · No NAV predictions · Non-transactional</span>
        </div>
      </div>
    </aside>
  );
}
