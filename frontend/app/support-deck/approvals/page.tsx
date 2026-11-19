"use client";

import { useCallback, useEffect, useState } from "react";
import {
  approveAction,
  getApprovals,
  rejectAction,
  type ApprovalAction,
} from "@/lib/support-deck-api";

function destinationsOf(action: ApprovalAction): string[] {
  const raw = action.payload_preview?.destinations;
  if (Array.isArray(raw)) return raw.map(String);
  if (typeof raw === "string") return [raw];
  return [];
}

export default function ApprovalsPage() {
  const [actions, setActions] = useState<ApprovalAction[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const list = await getApprovals();
    setActions(list);
  }, []);

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, [refresh]);

  const selected = actions.find((a) => a.action_id === selectedId) ?? null;

  async function onApprove() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await approveAction(selected.action_id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onReject() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await rejectAction(selected.action_id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-bold text-slate-900">Approvals</h1>
        <p className="mt-1 text-sm text-slate-600">
          Exact payload preview and destinations. Approve or reject one action at a time.
        </p>
      </header>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
          {actions.length === 0 && (
            <li className="px-4 py-6 text-sm text-slate-500">No approval actions.</li>
          )}
          {actions.map((a) => (
            <li key={a.action_id}>
              <button
                type="button"
                onClick={() => setSelectedId(a.action_id)}
                className={`w-full px-4 py-3 text-left ${
                  selectedId === a.action_id ? "bg-brand-50" : "hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-900">{a.type}</span>
                  <span className="text-[11px] font-semibold text-slate-600">{a.status}</span>
                </div>
                <p className="mt-0.5 truncate font-mono text-xs text-slate-500">
                  {a.action_id}
                </p>
              </button>
            </li>
          ))}
        </ul>

        <section className="rounded-md border border-slate-200 bg-white p-4">
          {!selected ? (
            <p className="text-sm text-slate-500">Select an action to inspect payload.</p>
          ) : (
            <div className="space-y-4">
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  {selected.type} · {selected.status}
                </h2>
                <p className="mt-1 font-mono text-xs text-slate-500">{selected.action_id}</p>
              </div>

              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Destinations
                </h3>
                {destinationsOf(selected).length === 0 ? (
                  <p className="mt-1 text-sm text-slate-500">None listed in payload.</p>
                ) : (
                  <ul className="mt-1 list-disc pl-5 text-sm text-slate-800">
                    {destinationsOf(selected).map((d) => (
                      <li key={d}>{d}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Payload preview
                </h3>
                <pre className="mt-1 max-h-80 overflow-auto rounded-md bg-slate-50 p-3 font-mono text-xs text-slate-800">
                  {JSON.stringify(selected.payload_preview, null, 2)}
                </pre>
              </div>

              {selected.edited_content && (
                <div>
                  <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Edited content
                  </h3>
                  <pre className="mt-1 whitespace-pre-wrap rounded-md bg-slate-50 p-3 text-sm text-slate-800">
                    {selected.edited_content}
                  </pre>
                </div>
              )}

              <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                <button
                  type="button"
                  onClick={onApprove}
                  disabled={busy || selected.status !== "pending_approval"}
                  className="rounded-md bg-brand-800 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40"
                >
                  Approve
                </button>
                <button
                  type="button"
                  onClick={onReject}
                  disabled={busy || selected.status !== "pending_approval"}
                  className="rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-semibold text-red-800 disabled:opacity-40"
                >
                  Reject
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
