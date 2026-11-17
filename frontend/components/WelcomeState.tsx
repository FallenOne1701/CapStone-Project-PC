"use client";

import { EXAMPLE_QUESTIONS } from "@/lib/types";

type Props = {
  onExample: (question: string) => void;
};

export function WelcomeState({ onExample }: Props) {
  return (
    <div className="my-auto space-y-7 py-4">
      <div className="space-y-2 border-b border-slate-100 pb-6 text-left">
        <div className="mb-1 inline-flex items-center gap-2 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-brand-800">
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
              d="M5 13l4 4L19 7"
            />
          </svg>
          Verified Scheme Information Document (SID) & KIM Data
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          Ask factual questions about HDFC mutual funds
        </h1>
        <p className="text-sm leading-relaxed text-slate-600 sm:text-base">
          Answers come from scheme sources only — short, cited, and
          non-advisory.
        </p>
      </div>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Example factual questions
          </span>
          <span className="text-xs text-slate-400">Click to ask instantly</span>
        </div>
        <div className="grid grid-cols-1 gap-2.5">
          {EXAMPLE_QUESTIONS.map((q, i) => (
            <button
              key={q}
              type="button"
              onClick={() => onExample(q)}
              className="group flex items-start justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/70 p-3.5 text-left transition-all hover:border-emerald-300 hover:bg-emerald-50/60"
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-md border border-slate-200 bg-white text-xs font-semibold text-slate-500 group-hover:border-emerald-300 group-hover:text-brand-800">
                  {i + 1}
                </div>
                <span className="text-sm font-medium leading-snug text-slate-800 group-hover:text-emerald-950">
                  “{q}”
                </span>
              </div>
              <svg
                className="mt-1 h-4 w-4 flex-shrink-0 text-slate-400 transition-all group-hover:translate-x-0.5 group-hover:text-brand-800"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                aria-hidden
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
          ))}
        </div>
      </div>

      <div className="flex items-start gap-3 rounded-xl border border-slate-200/80 bg-slate-50 p-3.5 text-xs text-slate-600">
        <div className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-slate-200/70 text-[11px] font-bold text-slate-600">
          i
        </div>
        <div>
          <p className="font-medium text-slate-700">
            Strict Compliance Guardrail:
          </p>
          <p className="mt-0.5 text-slate-500">
            I refuse advice questions like{" "}
            <span className="italic text-slate-700">“Should I invest?”</span>,{" "}
            <span className="italic text-slate-700">“Which fund is better?”</span>
            , or queries asking for returns predictions.
          </p>
        </div>
      </div>
    </div>
  );
}
