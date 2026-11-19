"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AgentPackagePanels } from "@/components/support-deck/AgentPackagePanels";
import { DeckAlert } from "@/components/support-deck/DeckAlert";
import { MaterialIcon } from "@/components/support-deck/MaterialIcon";
import { StatusBadge } from "@/components/support-deck/StatusBadge";
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
  type QueueStatus,
} from "@/lib/support-deck-api";

const SAMPLE_QUESTIONS = [
  {
    text: "What is the exit load if I redeem within 7 days?",
    icon: "data_exploration",
  },
  {
    text: "How are Groww brokerage and mutual fund charges explained?",
    icon: "currency_rupee",
  },
  {
    text: "Where can I find the official mutual fund scheme information?",
    icon: "description",
  },
] as const;

type FilterKey = "all" | QueueStatus;

export default function QueuePage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [actions, setActions] = useState<ApprovalAction[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftEdit, setDraftEdit] = useState("");
  const [question, setQuestion] = useState("");
  const [filter, setFilter] = useState<FilterKey>("all");
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

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    for (const item of items) {
      c[item.status] = (c[item.status] ?? 0) + 1;
    }
    return c;
  }, [items]);

  const filtered = useMemo(
    () => (filter === "all" ? items : items.filter((i) => i.status === filter)),
    [items, filter],
  );

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

  const draftDirty = !!selected && draftEdit !== (selected.draft ?? "");
  const draftLocked =
    selected?.status === "approved" || selected?.status === "rejected";

  const wordCount = draftEdit.trim()
    ? draftEdit.trim().split(/\s+/).length
    : 0;

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

  const filters: { key: FilterKey; label: string }[] = [
    { key: "all", label: `All (${counts.all ?? 0})` },
    { key: "pending", label: `Pending (${counts.pending ?? 0})` },
    { key: "drafted", label: `Drafted (${counts.drafted ?? 0})` },
    { key: "approved", label: `Approved (${counts.approved ?? 0})` },
  ];

  return (
    <div className="flex w-full flex-col">
      {/* Ingestion controls */}
      <div className="mb-space-lg rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
        <div className="flex flex-col justify-between gap-space-md pb-space-md lg:flex-row lg:items-center">
          <div>
            <h1 className="font-headline-md text-headline-md font-bold tracking-tight text-on-surface">
              Queue
            </h1>
            <p className="mt-0.5 font-body-sm text-body-sm text-on-surface-variant">
              Questions, drafts, citations, and reply approve/reject workflow.
              Approve records human sign-off — it does not generate the answer.
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-space-sm pb-space-sm pt-space-xs">
          <span className="font-label-sm text-label-sm font-semibold uppercase tracking-wider text-on-surface-variant">
            Test ingestion:
          </span>
          {SAMPLE_QUESTIONS.map((sample) => (
            <button
              key={sample.text}
              type="button"
              disabled={busy}
              onClick={() => setQuestion(sample.text)}
              className={`flex items-center gap-1.5 rounded-full px-space-md py-1 text-left font-label-md text-label-md shadow-sm transition-colors disabled:opacity-50 ${
                question === sample.text
                  ? "bg-secondary-container text-on-secondary-container"
                  : "bg-surface-container text-on-surface hover:bg-surface-container-high"
              }`}
            >
              <MaterialIcon
                name={sample.icon}
                className="text-[15px] text-primary"
              />
              {sample.text}
            </button>
          ))}
        </div>

        <form
          onSubmit={onEnqueue}
          className="flex items-center gap-space-sm pt-space-xs"
        >
          <div className="relative flex-1">
            <MaterialIcon
              name="search"
              className="absolute left-3 top-1/2 -translate-y-1/2 text-lg text-on-surface-variant"
            />
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Type incoming customer question…"
              className="h-10 w-full rounded-lg bg-surface pl-9 pr-space-md font-body-md text-body-md text-on-surface shadow-inner transition-colors placeholder:text-on-surface-variant/70 focus:bg-surface-container-low focus:outline-none"
            />
          </div>
          <button
            type="submit"
            disabled={busy || !question.trim()}
            className="flex h-10 flex-shrink-0 items-center gap-1.5 rounded-lg bg-primary px-space-xl font-label-md text-label-md font-medium text-on-primary shadow-sm transition-all hover:bg-tertiary disabled:opacity-50"
          >
            <MaterialIcon name="send" className="text-[17px]" />
            {busy ? "Running Retrieve · Draft · Policy…" : "Enqueue"}
          </button>
        </form>
      </div>

      {error && (
        <div className="mb-space-lg">
          <DeckAlert tone="error">{error}</DeckAlert>
        </div>
      )}

      <div className="grid w-full grid-cols-1 items-start gap-space-lg xl:grid-cols-12">
        {/* Left: ticket stream */}
        <div className="flex w-full flex-col overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm xl:col-span-5">
          <div className="flex flex-col gap-space-sm bg-surface-container-low p-space-md">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-space-sm">
                <span className="font-headline-sm text-headline-sm font-bold text-on-surface">
                  Active tickets
                </span>
                <span className="rounded-full bg-secondary-container px-2 py-0.5 font-code-sm text-code-sm font-semibold text-on-secondary-container">
                  {items.length}
                </span>
              </div>
              <button
                type="button"
                onClick={() => refresh().catch((e: Error) => setError(e.message))}
                disabled={busy}
                className="rounded p-1 text-on-surface-variant hover:bg-surface-container"
                title="Refresh"
              >
                <MaterialIcon name="refresh" className="text-sm" />
              </button>
            </div>
            <div className="flex w-full items-center gap-1 rounded-lg bg-surface-container p-0.5">
              {filters.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setFilter(f.key)}
                  className={`flex-1 rounded py-1 text-center font-label-sm text-label-sm ${
                    filter === f.key
                      ? "bg-surface-container-lowest font-semibold text-primary shadow-sm"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex max-h-[720px] flex-col divide-y divide-surface-container-low overflow-y-auto">
            {filtered.length === 0 && (
              <p className="px-space-md py-6 font-body-sm text-body-sm text-on-surface-variant">
                No queue items yet.
              </p>
            )}
            {filtered.map((item) => {
              const active = selectedId === item.question_id;
              return (
                <button
                  key={item.question_id}
                  type="button"
                  onClick={() => setSelectedId(item.question_id)}
                  className={`relative w-full p-space-md text-left transition-colors ${
                    active
                      ? "bg-secondary-container/40 hover:bg-secondary-container/60"
                      : "bg-surface-container-lowest hover:bg-surface-container-low"
                  }`}
                >
                  {active && (
                    <span className="absolute bottom-0 left-0 top-0 w-1 bg-primary" />
                  )}
                  <div className="mb-1 flex items-start justify-between gap-space-sm">
                    <span
                      className={`flex items-center gap-1 font-code-sm text-code-sm font-medium ${
                        active ? "text-primary" : "text-on-surface-variant"
                      }`}
                    >
                      {active && (
                        <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                      )}
                      {item.question_id}
                    </span>
                    <StatusBadge status={item.status} />
                  </div>
                  <p className="mb-1.5 line-clamp-2 font-body-md text-body-md font-semibold leading-snug text-on-surface">
                    {item.question_text || item.question_id}
                  </p>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {item.routing_note && (
                      <p className="font-code-sm text-code-sm text-on-surface-variant">
                        route: {item.routing_note}
                      </p>
                    )}
                    {item.agent_package?.pattern?.recurring && (
                      <span className="rounded bg-amber-100 px-1.5 py-0.5 font-label-sm text-label-sm font-semibold text-amber-900">
                        recurring
                      </span>
                    )}
                    {item.agent_package?.reviewer?.passed === false && (
                      <span className="rounded bg-error-container px-1.5 py-0.5 font-label-sm text-label-sm font-semibold text-on-error-container">
                        reviewer fail
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: detail pane */}
        <div className="flex w-full flex-col overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm xl:col-span-7">
          {!selected ? (
            <p className="p-space-lg font-body-sm text-body-sm text-on-surface-variant">
              Select a queue item to open detail.
            </p>
          ) : (
            <>
              <div className="flex flex-col gap-space-sm bg-surface-container-low p-space-lg">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-surface-container-lowest px-2 py-0.5 font-code-sm text-code-sm font-semibold text-primary shadow-sm">
                    ticket: {selected.question_id}
                  </span>
                  <StatusBadge status={selected.status} />
                  {selected.routing_note && (
                    <span className="rounded bg-surface-container px-2 py-0.5 font-code-sm text-code-sm text-on-surface-variant">
                      routing_note: {selected.routing_note}
                    </span>
                  )}
                  {selected.explainer_id && (
                    <span className="rounded bg-surface-container px-2 py-0.5 font-code-sm text-code-sm text-on-surface-variant">
                      explainer_id: {selected.explainer_id}
                    </span>
                  )}
                </div>
                <div className="pt-space-xs">
                  <span className="mb-1 block font-label-sm text-label-sm font-semibold uppercase text-on-surface-variant">
                    Customer query
                  </span>
                  <p className="font-headline-sm text-headline-sm font-semibold leading-snug text-on-surface">
                    “{selected.question_text}”
                  </p>
                  <p className="mt-1 font-label-sm text-label-sm text-on-surface-variant">
                    PII redacted at ingress before agents run.
                  </p>
                </div>
              </div>

              {selected.reviewer_flags.length > 0 && (
                <div className="border-b border-surface-container bg-amber-50 px-space-lg py-2 font-body-sm text-body-sm text-amber-900">
                  Flags: {selected.reviewer_flags.join(", ")}
                </div>
              )}

              <div className="flex flex-col gap-space-sm bg-surface-container-lowest p-space-lg">
                <div className="flex items-center justify-between gap-space-sm">
                  <div className="flex flex-wrap items-center gap-space-sm">
                    <span className="font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
                      Proposed customer reply
                    </span>
                    <span className="flex items-center gap-1 rounded bg-surface-container px-2 py-0.5 font-label-sm text-label-sm font-medium text-on-surface-variant">
                      <MaterialIcon name="edit_note" className="text-[13px]" />
                      {draftLocked
                        ? "Locked after decision"
                        : draftDirty
                          ? "Unsaved edits"
                          : "Editable before approval"}
                    </span>
                  </div>
                  <span className="font-code-sm text-code-sm text-on-surface-variant">
                    {wordCount} words · {draftEdit.length} characters
                  </span>
                </div>
                <div className="relative w-full rounded-lg bg-surface p-space-sm shadow-inner transition-all focus-within:bg-surface-container-lowest focus-within:ring-2 focus-within:ring-primary">
                  <textarea
                    value={draftEdit}
                    onChange={(e) => setDraftEdit(e.target.value)}
                    rows={10}
                    readOnly={draftLocked}
                    className="w-full resize-y bg-transparent font-body-md text-body-md leading-relaxed text-on-surface focus:outline-none read-only:text-on-surface-variant"
                  />
                </div>
                <div className="flex items-center justify-between pt-1">
                  <button
                    type="button"
                    onClick={onSaveDraft}
                    disabled={busy || !draftDirty || draftLocked}
                    className="flex items-center gap-1.5 rounded-lg bg-surface-container px-space-md py-1.5 font-label-md text-label-md font-medium text-on-surface shadow-sm transition-colors hover:bg-surface-container-high disabled:opacity-50"
                  >
                    <MaterialIcon
                      name="save"
                      className="text-[16px] text-primary"
                    />
                    Save draft
                  </button>
                </div>
              </div>

              <AgentPackagePanels pkg={selected.agent_package} />

              <div className="flex flex-col gap-space-sm bg-surface-container-low px-space-lg py-space-md">
                <span className="font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
                  Grounding &amp; evidence
                </span>
                <div className="flex items-center justify-between gap-space-sm rounded-lg bg-surface-container-lowest p-space-sm shadow-sm">
                  <div className="flex min-w-0 items-center gap-space-sm">
                    <MaterialIcon
                      name="verified_user"
                      className="flex-shrink-0 text-lg text-primary"
                    />
                    <div className="flex min-w-0 flex-col">
                      <span className="font-label-sm text-label-sm font-semibold text-on-surface">
                        Citation
                      </span>
                      {selected.citation_url ? (
                        <a
                          href={selected.citation_url}
                          target="_blank"
                          rel="noreferrer"
                          className="flex items-center gap-1 truncate font-code-sm text-code-sm text-primary hover:underline"
                        >
                          {selected.citation_url}
                          <MaterialIcon
                            name="open_in_new"
                            className="text-xs"
                          />
                        </a>
                      ) : (
                        <span className="font-code-sm text-code-sm text-on-surface-variant">
                          —
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                {selected.searched.length > 0 && (
                  <div className="space-y-1 rounded-lg bg-surface-container-lowest p-space-sm font-code-sm text-code-sm text-on-surface-variant">
                    <div className="text-[11px] font-semibold uppercase tracking-wider text-on-surface">
                      Searched
                    </div>
                    {selected.searched.map((s, i) => (
                      <div key={s} className="flex items-center gap-1 truncate text-on-surface">
                        <span className="font-bold text-primary">{i + 1}.</span>
                        {s}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex flex-col items-center justify-between gap-space-md bg-surface-container-lowest p-space-lg shadow-deck-sticky sm:flex-row">
                {selected.status === "approved" && (
                  <p className="font-body-md text-body-md font-medium text-on-secondary-container">
                    Reply approved — this item is finalized.
                  </p>
                )}
                {selected.status === "rejected" && (
                  <p className="font-body-md text-body-md font-medium text-on-error-container">
                    Reply rejected — this item will not be finalized.
                  </p>
                )}
                {(selected.status === "drafted" ||
                  selected.status === "pending") && (
                  <>
                    <div className="flex items-center gap-space-sm">
                      <span className="h-2.5 w-2.5 flex-shrink-0 animate-pulse rounded-full bg-secondary" />
                      <span className="font-body-md text-body-md font-medium text-on-surface">
                        Awaiting human sign-off for customer dispatch.
                      </span>
                    </div>
                    <div className="flex w-full items-center justify-end gap-space-sm sm:w-auto">
                      <button
                        type="button"
                        onClick={onRejectReply}
                        disabled={busy || !replyAction}
                        className="flex items-center gap-1.5 rounded-lg bg-surface-container-low px-space-md py-2 font-label-md text-label-md font-semibold text-error transition-all hover:bg-error-container hover:text-on-error-container disabled:opacity-40"
                      >
                        <MaterialIcon name="close" className="text-[17px]" />
                        Reject reply
                      </button>
                      <button
                        type="button"
                        onClick={onApproveReply}
                        disabled={busy || !replyAction}
                        className="flex items-center gap-2 rounded-lg bg-primary px-space-xl py-2 font-label-md text-label-md font-semibold text-on-primary shadow-sm transition-all hover:bg-tertiary disabled:opacity-40"
                      >
                        <MaterialIcon
                          name="check_circle"
                          className="text-[18px]"
                        />
                        Approve reply
                      </button>
                    </div>
                  </>
                )}
              </div>
              {(selected.status === "drafted" ||
                selected.status === "pending") &&
                !replyAction && (
                  <div className="bg-surface-container px-space-lg py-space-xs text-center">
                    <span className="font-code-sm text-code-sm text-on-surface-variant">
                      No pending reply_finalize for this item.
                    </span>
                  </div>
                )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
