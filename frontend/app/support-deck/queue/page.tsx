"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  approveAction,
  enqueueQuestion,
  findPendingReplyAction,
  getApprovals,
  getQueue,
  patchQueueDraft,
  rejectAction,
  type ApprovalAction,
  type QueueItem,
} from "@/lib/support-deck-api";

export default function QueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [actions, setActions] = useState<ApprovalAction[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftEdit, setDraftEdit] = useState("");
  const [question, setQuestion] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setError(null);
    const [q, a] = await Promise.all([getQueue(), getApprovals()]);
    setItems(q);
    setActions(a);
  }, []);

  useEffect(() => {
    refresh().catch((e: Error) => setError(e.message));
  }, [refresh]);

  const selected = useMemo(
    () => items.find((i) => i.question_id === selectedId) ?? null,
    [items, selectedId],
  );

  useEffect(() => {
    setDraftEdit(selected?.draft ?? "");
  }, [selected]);

  const replyAction = selected
    ? findPendingReplyAction(actions, selected.question_id)
    : undefined;

  async function onEnqueue(e: React.FormEvent) {
    e.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const item = await enqueueQuestion(question.trim());
      setQuestion("");
      await refresh();
      setSelectedId(item.question_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onSaveDraft() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await patchQueueDraft(selected.question_id, draftEdit);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onApproveReply() {
    if (!replyAction) return;
    setBusy(true);
    setError(null);
    try {
      await approveAction(replyAction.action_id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function onRejectReply() {
    if (!replyAction) return;
    setBusy(true);
    setError(null);
    try {
      await rejectAction(replyAction.action_id);
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
        <h1 className="text-xl font-bold text-slate-900">Queue</h1>
        <p className="mt-1 text-sm text-slate-600">
          Questions, drafts, citations, and reply approve/reject.
        </p>
      </header>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      <form onSubmit={onEnqueue} className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Enqueue a support question…"
          className="flex-1 rounded-md border border-slate-300 bg-white px-3 py-2 text-sm outline-none focus:border-brand-700 focus:ring-1 focus:ring-brand-700"
        />
        <button
          type="submit"
          disabled={busy || !question.trim()}
          className="rounded-md bg-brand-800 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
        >
          Enqueue
        </button>
      </form>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <ul className="divide-y divide-slate-200 rounded-md border border-slate-200 bg-white">
          {items.length === 0 && (
            <li className="px-4 py-6 text-sm text-slate-500">No queue items yet.</li>
          )}
          {items.map((item) => (
            <li key={item.question_id}>
              <button
                type="button"
                onClick={() => setSelectedId(item.question_id)}
                className={`w-full px-4 py-3 text-left transition-colors ${
                  selectedId === item.question_id
                    ? "bg-brand-50"
                    : "hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-semibold text-slate-900">
                    {item.question_text || item.question_id}
                  </span>
                  <StatusPill status={item.status} />
                </div>
                <p className="mt-0.5 truncate font-mono text-xs text-slate-500">
                  {item.question_id}
                </p>
              </button>
            </li>
          ))}
        </ul>

        <section className="rounded-md border border-slate-200 bg-white p-4">
          {!selected ? (
            <p className="text-sm text-slate-500">Select a queue item to open detail.</p>
          ) : (
            <div className="space-y-4">
              <div>
                <h2 className="text-sm font-bold text-slate-900">Detail</h2>
                <p className="mt-1 text-sm text-slate-800">{selected.question_text}</p>
                <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600">
                  <StatusPill status={selected.status} />
                  {selected.routing_note && (
                    <span className="rounded border border-slate-200 px-2 py-0.5">
                      {selected.routing_note}
                    </span>
                  )}
                  {selected.explainer_id && (
                    <span className="rounded border border-slate-200 px-2 py-0.5">
                      explainer: {selected.explainer_id}
                    </span>
                  )}
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Draft
                </label>
                <textarea
                  value={draftEdit}
                  onChange={(e) => setDraftEdit(e.target.value)}
                  rows={6}
                  className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-700 focus:ring-1 focus:ring-brand-700"
                />
                <button
                  type="button"
                  onClick={onSaveDraft}
                  disabled={busy || draftEdit === (selected.draft ?? "")}
                  className="mt-2 rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-800 disabled:opacity-50"
                >
                  Save draft
                </button>
              </div>

              <div className="space-y-1 text-sm">
                <p>
                  <span className="font-semibold text-slate-700">Citation: </span>
                  {selected.citation_url ? (
                    <a
                      href={selected.citation_url}
                      className="text-brand-800 underline"
                      target="_blank"
                      rel="noreferrer"
                    >
                      {selected.citation_url}
                    </a>
                  ) : (
                    <span className="text-slate-500">—</span>
                  )}
                </p>
                {selected.reviewer_flags.length > 0 && (
                  <p>
                    <span className="font-semibold text-slate-700">Flags: </span>
                    {selected.reviewer_flags.join(", ")}
                  </p>
                )}
                {selected.searched.length > 0 && (
                  <p className="text-xs text-slate-500">
                    Searched: {selected.searched.join(" · ")}
                  </p>
                )}
              </div>

              <div className="flex flex-wrap gap-2 border-t border-slate-100 pt-3">
                <button
                  type="button"
                  onClick={onApproveReply}
                  disabled={busy || !replyAction}
                  className="rounded-md bg-brand-800 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-40"
                >
                  Approve reply
                </button>
                <button
                  type="button"
                  onClick={onRejectReply}
                  disabled={busy || !replyAction}
                  className="rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-semibold text-red-800 disabled:opacity-40"
                >
                  Reject reply
                </button>
                {!replyAction && selected.status === "drafted" && (
                  <span className="self-center text-xs text-slate-500">
                    No pending reply_finalize for this item.
                  </span>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const tone =
    status === "drafted" || status === "approved"
      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
      : status === "rejected" || status === "not_covered"
        ? "border-amber-200 bg-amber-50 text-amber-900"
        : "border-slate-200 bg-slate-50 text-slate-700";
  return (
    <span className={`inline-flex rounded border px-2 py-0.5 text-[11px] font-semibold ${tone}`}>
      {status}
    </span>
  );
}
