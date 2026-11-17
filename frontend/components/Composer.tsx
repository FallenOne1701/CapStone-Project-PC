"use client";

type Props = {
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
};

export function Composer({ value, disabled, onChange, onSubmit }: Props) {
  return (
    <div className="border-t border-slate-200/90 bg-slate-50/70 p-4 sm:p-5">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="relative"
      >
        <div className="relative rounded-xl border border-slate-300 bg-white shadow-sm transition-all focus-within:border-brand-800 focus-within:ring-2 focus-within:ring-emerald-100">
          <textarea
            rows={2}
            value={value}
            disabled={disabled}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                onSubmit();
              }
            }}
            placeholder="Ask a factual question about the 5 covered HDFC schemes (e.g. exit load, expense ratio)..."
            className="w-full resize-none bg-transparent px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none disabled:opacity-60"
          />
          <div className="flex items-center justify-between rounded-b-xl border-t border-slate-100 bg-slate-50/40 px-3 py-2">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span className="hidden sm:inline">
                Press Enter to Ask · Fact citations included
              </span>
              <span className="sm:hidden">Factual only</span>
            </div>
            <button
              type="submit"
              disabled={disabled || !value.trim()}
              className="inline-flex items-center gap-1.5 rounded-lg bg-brand-800 px-4 py-1.5 text-xs font-semibold text-white shadow-sm transition-all hover:bg-brand-900 disabled:pointer-events-none disabled:opacity-50"
            >
              {disabled ? (
                <>
                  <svg
                    className="-ml-1 mr-1 h-3.5 w-3.5 animate-spin text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    aria-hidden
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8v8H4z"
                    />
                  </svg>
                  Checking...
                </>
              ) : (
                <>
                  <span>Ask</span>
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
                      d="M14 5l7 7m0 0l-7 7m7-7H3"
                    />
                  </svg>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
      <p className="mt-2 text-center text-[11px] font-medium text-slate-400">
        Educational prototype · Not investment advice · No personal data
        collected
      </p>
    </div>
  );
}
