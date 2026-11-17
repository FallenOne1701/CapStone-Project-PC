"use client";

import { EXAMPLE_QUESTIONS, type RefusalResponse } from "@/lib/types";

type Props = {
  question: string;
  data: RefusalResponse;
  onExample: (question: string) => void;
};

export function RefusalMessage({ question, data, onExample }: Props) {
  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm border border-slate-200/80 bg-slate-100 px-4 py-3 text-sm font-medium text-slate-900">
          {question}
        </div>
      </div>
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-amber-700 text-xs font-bold text-white shadow-sm">
          HF
        </div>
        <div className="max-w-[92%] space-y-4 rounded-2xl rounded-tl-sm border border-amber-200/80 bg-amber-50/40 p-5 shadow-sm">
          <div className="flex items-center justify-between border-b border-amber-200/60 pb-2.5">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-300/70 bg-amber-100 px-2 py-0.5 text-xs font-bold text-amber-900">
              <svg
                className="h-3.5 w-3.5 text-amber-700"
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
              Non-Advisory Query Refused
            </span>
            <span className="text-xs font-medium text-amber-800">
              Facts-only policy
            </span>
          </div>
          <div className="space-y-2 text-sm leading-relaxed text-slate-800">
            <p className="font-medium text-slate-900">{data.answer}</p>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <a
              href={data.educational_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-sm transition-colors hover:bg-slate-50"
            >
              Learn more on AMFI Investor Education
            </a>
          </div>
          <div className="space-y-2 border-t border-amber-200/60 pt-3">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-600">
              Try asking a factual question instead:
            </span>
            <div className="flex flex-col gap-1.5">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => onExample(q)}
                  className="flex items-center justify-between rounded-lg border border-slate-200 bg-white/80 p-2 text-left text-xs text-slate-700 transition-colors hover:bg-white hover:text-emerald-800"
                >
                  <span>{q}</span>
                  <span className="font-bold text-brand-800">→</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
