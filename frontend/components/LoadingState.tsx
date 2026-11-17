type Props = {
  question: string;
};

export function LoadingState({ question }: Props) {
  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-tr-sm border border-slate-200/80 bg-slate-100 px-4 py-3 text-sm font-medium text-slate-900 shadow-sm">
          {question}
        </div>
      </div>
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg bg-brand-800 text-xs font-bold text-white shadow-sm">
          HF
        </div>
        <div className="max-w-[85%] space-y-2 rounded-2xl rounded-tl-sm border border-slate-200 bg-white p-4 shadow-sm">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-600">
            <div className="flex items-center gap-1">
              <span className="inline-block h-2 w-2 animate-dot-1 rounded-full bg-brand-800" />
              <span className="inline-block h-2 w-2 animate-dot-2 rounded-full bg-brand-800" />
              <span className="inline-block h-2 w-2 animate-dot-3 rounded-full bg-brand-800" />
            </div>
            <span>Checking scheme sources…</span>
          </div>
          <p className="text-xs text-slate-400">
            Verifying scheme facts from the indexed Groww corpus.
          </p>
        </div>
      </div>
    </div>
  );
}
