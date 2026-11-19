"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  getPulse,
  runWeekly,
  type ApprovalAction,
  type PulsePayload,
} from "@/lib/support-deck-api";

type ThemeRow = {
  theme_id?: string;
  label?: string;
  count?: number;
  review_ids?: string[];
  quotes?: string[];
};

function asThemes(raw: unknown): ThemeRow[] {
  if (Array.isArray(raw)) return raw as ThemeRow[];
  if (raw && typeof raw === "object" && Array.isArray((raw as { themes?: unknown }).themes)) {
    return (raw as { themes: ThemeRow[] }).themes;
  }
  return [];
}

export default function PulsePage() {
  const [pulse, setPulse] = useState<PulsePayload | null>(null);
  const [pendingActions, setPendingActions] = useState<ApprovalAction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [live, setLive] = useState(false);

  const loadPulse = useCallback(async () => {
    try {
      const data = await getPulse();
      setPulse(data);
      setError(null);
    } catch (err) {
      setPulse(null);
      setError(err instanceof Error ? err.message : String(err));
    }
  }, []);

  useEffect(() => {
    loadPulse();
  }, [loadPulse]);

  async function onPreparePublish() {
    setBusy(true);
    setError(null);
    try {
      const result = await runWeekly(live);
      setPendingActions(result.actions);
      await loadPulse();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  const themes = pulse ? asThemes(pulse.themes) : [];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Weekly pulse</h1>
          <p className="mt-1 text-sm text-slate-600">
            Themes, window, and review-id traces. Prepare publish creates pending approvals.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={live}
              onChange={(e) => setLive(e.target.checked)}
              className="rounded border-slate-300"
            />
            Live Play ingest
          </label>
          <button
            type="button"
            onClick={onPreparePublish}
            disabled={busy}
            className="rounded-md bg-brand-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? "Running…" : "Prepare publish"}
          </button>
        </div>
      </header>

      {error && (
        <p className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          {error}
        </p>
      )}

      {pendingActions.length > 0 && (
        <div className="rounded-md border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-900">
          Created {pendingActions.length} pending action
          {pendingActions.length === 1 ? "" : "s"}.{" "}
          <Link href="/support-deck/approvals" className="font-semibold underline">
            Open Approvals
          </Link>
        </div>
      )}

      {pulse && (
        <div className="space-y-4">
          <dl className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
              <dt className="text-xs font-semibold uppercase text-slate-500">Window</dt>
              <dd className="mt-1 text-sm text-slate-900">
                {pulse.window_start} → {pulse.window_end}
              </dd>
            </div>
            <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
              <dt className="text-xs font-semibold uppercase text-slate-500">Lookback</dt>
              <dd className="mt-1 text-sm text-slate-900">{pulse.lookback_weeks} weeks</dd>
            </div>
            <div className="rounded-md border border-slate-200 bg-white px-3 py-2">
              <dt className="text-xs font-semibold uppercase text-slate-500">Mode</dt>
              <dd className="mt-1 text-sm text-slate-900">{pulse.live ? "live" : "sample"}</dd>
            </div>
          </dl>

          <section className="rounded-md border border-slate-200 bg-white">
            <h2 className="border-b border-slate-100 px-4 py-2 text-sm font-bold text-slate-900">
              Themes
            </h2>
            {themes.length === 0 ? (
              <p className="px-4 py-4 text-sm text-slate-500">No themes in latest pulse.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {themes.map((t, idx) => (
                  <li key={t.theme_id ?? idx} className="px-4 py-3">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <span className="text-sm font-semibold text-slate-900">
                        {t.label ?? t.theme_id ?? `Theme ${idx + 1}`}
                      </span>
                      {typeof t.count === "number" && (
                        <span className="text-xs font-medium text-slate-500">
                          count {t.count}
                        </span>
                      )}
                    </div>
                    {t.review_ids && t.review_ids.length > 0 && (
                      <p className="mt-1 font-mono text-xs text-slate-500">
                        review ids: {t.review_ids.join(", ")}
                      </p>
                    )}
                    {t.quotes && t.quotes.length > 0 && (
                      <ul className="mt-2 space-y-1 text-sm text-slate-700">
                        {t.quotes.map((q, i) => (
                          <li key={i} className="border-l-2 border-slate-200 pl-2 italic">
                            “{q}”
                          </li>
                        ))}
                      </ul>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="rounded-md border border-slate-200 bg-white p-4">
            <h2 className="text-sm font-bold text-slate-900">Pulse markdown</h2>
            <pre className="mt-2 max-h-96 overflow-auto whitespace-pre-wrap font-mono text-xs text-slate-800">
              {pulse.pulse_markdown || "(empty)"}
            </pre>
          </section>
        </div>
      )}
    </div>
  );
}
