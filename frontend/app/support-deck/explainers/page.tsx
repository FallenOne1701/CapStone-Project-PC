"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  getExplainers,
  getQueue,
  runWeekly,
  type ApprovalAction,
  type FeeExplainer,
  type QueueItem,
} from "@/lib/support-deck-api";

export default function ExplainersPage() {
  const [explainers, setExplainers] = useState<FeeExplainer[]>([]);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [pendingActions, setPendingActions] = useState<ApprovalAction[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const [e, q] = await Promise.all([getExplainers(), getQueue()]);
    setExplainers(e);
    setQueue(q);
  }, []);

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, [refresh]);

  const reuseCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const item of queue) {
      if (!item.explainer_id) continue;
      map.set(item.explainer_id, (map.get(item.explainer_id) ?? 0) + 1);
    }
    return map;
  }, [queue]);

  async function onPreparePublish() {
    setBusy(true);
    setError(null);
    try {
      const result = await runWeekly(false);
      setPendingActions(result.actions);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Explainers</h1>
          <p className="mt-1 text-sm text-slate-600">
            Canonical fee explainers — active flag and reuse count from the queue.
          </p>
        </div>
        <button
          type="button"
          onClick={onPreparePublish}
          disabled={busy}
          className="rounded-md bg-brand-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          {busy ? "Running…" : "Prepare publish"}
        </button>
      </header>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
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

      <ul className="space-y-4">
        {explainers.length === 0 && (
          <li className="rounded-md border border-slate-200 bg-white px-4 py-6 text-sm text-slate-500">
            No explainers yet. Run weekly prepare publish or seed via API.
          </li>
        )}
        {explainers.map((ex) => {
          const id = ex.explainer_id ?? "(no id)";
          const reuse = ex.explainer_id
            ? (reuseCounts.get(ex.explainer_id) ?? 0)
            : 0;
          return (
            <li
              key={id}
              className="rounded-md border border-slate-200 bg-white p-4"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-mono text-sm font-bold text-slate-900">{id}</h2>
                <div className="flex flex-wrap gap-2 text-xs">
                  <span
                    className={`rounded border px-2 py-0.5 font-semibold ${
                      ex.active
                        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                        : "border-slate-200 bg-slate-50 text-slate-600"
                    }`}
                  >
                    {ex.active ? "active" : "inactive"}
                  </span>
                  <span className="rounded border border-slate-200 px-2 py-0.5 font-medium text-slate-700">
                    reuse count: {reuse}
                  </span>
                  <span className="rounded border border-slate-200 px-2 py-0.5 text-slate-600">
                    last checked: {ex.last_checked}
                  </span>
                </div>
              </div>
              <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-800">
                {ex.bullets.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ol>
              <ul className="mt-3 space-y-1 text-sm">
                {ex.links.map((url) => (
                  <li key={url}>
                    <a
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-brand-800 underline"
                    >
                      {url}
                    </a>
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
