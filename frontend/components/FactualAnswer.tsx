import type { FactualResponse } from "@/lib/types";

type Props = {
  question: string;
  data: FactualResponse;
};

function formatDate(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function FactualAnswer({ question, data }: Props) {
  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm border border-slate-200/80 bg-slate-100 px-4 py-3 text-sm font-medium text-slate-900">
          {question}
        </div>
      </div>
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-brand-800 text-xs font-bold text-white shadow-sm">
          HF
        </div>
        <div className="max-w-[92%] space-y-4 rounded-2xl rounded-tl-sm border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-slate-100 pb-2.5">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2 py-0.5 text-xs font-bold text-brand-800">
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
                    strokeWidth="2.5"
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                Factual
              </span>
              {data.scheme_id ? (
                <span className="text-xs font-medium text-slate-600">
                  {data.scheme_id.replace(/-/g, " ")}
                </span>
              ) : null}
            </div>
          </div>
          <div className="space-y-2 text-sm leading-relaxed text-slate-800">
            {data.answer.split(/\n+/).map((p) => (
              <p key={p.slice(0, 24)}>{p}</p>
            ))}
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-2 text-xs">
            <a
              href={data.citation_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-md border border-emerald-200/70 bg-emerald-50/80 px-2.5 py-1.5 font-semibold text-brand-800 transition-colors hover:text-brand-900"
            >
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
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
              <span>View source</span>
            </a>
            <span className="text-[11px] text-slate-400">
              Last updated from sources: {formatDate(data.last_updated)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
