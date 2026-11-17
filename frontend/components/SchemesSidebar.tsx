const SCHEMES = [
  { title: "1. HDFC Mid Cap Fund", meta: "Direct Plan Growth · Equity Mid Cap" },
  {
    title: "2. HDFC Small Cap Fund",
    meta: "Direct Plan Growth · Equity Small Cap",
  },
  {
    title: "3. HDFC Gold ETF Fund of Fund",
    meta: "Direct Plan Growth · Commodities/Gold",
  },
  {
    title: "4. HDFC Large Cap Fund",
    meta: "Direct Plan Growth · Equity Large Cap",
  },
  {
    title: "5. HDFC ELSS Tax Saver Fund",
    meta: "Direct Plan Growth · Section 80C Tax Saver",
  },
];

const TOPICS = [
  "Expense ratio (TER)",
  "Exit load structure",
  "Minimum SIP / Lumpsum",
  "ELSS 3-yr Lock-in",
  "Riskometer category",
  "Benchmark Index",
  "Fund manager tenure",
];

export function SchemesSidebar() {
  return (
    <aside className="w-full flex-shrink-0 space-y-5 lg:w-[320px]">
      <div className="rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
              Covered Schemes (5)
            </h2>
          </div>
          <span className="rounded bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-500">
            HDFC AMC
          </span>
        </div>
        <p className="mb-3 mt-2.5 text-xs leading-relaxed text-slate-500">
          Questions are strictly answered for these 5 direct growth schemes:
        </p>
        <ul className="space-y-2">
          {SCHEMES.map((s) => (
            <li
              key={s.title}
              className="rounded-xl border border-slate-100 bg-slate-50/60 p-2.5 text-xs hover:border-slate-200"
            >
              <span className="block font-bold leading-tight text-slate-900">
                {s.title}
              </span>
              <span className="mt-0.5 block text-[11px] text-slate-500">
                {s.meta}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div className="space-y-3 rounded-2xl border border-slate-200/90 bg-white p-5 shadow-sm">
        <div className="flex items-center gap-2 border-b border-slate-100 pb-2">
          <svg
            className="h-4 w-4 text-brand-800"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800">
            What I Can Answer
          </h2>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {TOPICS.map((t) => (
            <span
              key={t}
              className="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-700"
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      <div className="space-y-2 rounded-2xl border border-slate-200/80 bg-slate-50 p-4 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-700">
          <svg
            className="h-4 w-4 text-slate-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
            />
          </svg>
          <span>Guaranteed Refusal Topics</span>
        </div>
        <ul className="list-inside list-disc space-y-1 text-[11px] leading-relaxed text-slate-500">
          <li>“Should I buy / sell now?”</li>
          <li>“Which scheme gives highest return?”</li>
          <li>“Rank these funds against peers”</li>
          <li>Predictions or NAV targets</li>
        </ul>
      </div>
    </aside>
  );
}
