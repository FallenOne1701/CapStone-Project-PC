"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { DeckAlert } from "@/components/support-deck/DeckAlert";
import { MaterialIcon } from "@/components/support-deck/MaterialIcon";
import { StatusBadge } from "@/components/support-deck/StatusBadge";
import {
  approveAction,
  getApprovals,
  rejectAction,
  type ApprovalAction,
  type ApprovalActionType,
} from "@/lib/support-deck-api";

function destinationsOf(action: ApprovalAction): string[] {
  const raw = action.payload_preview?.destinations;
  if (Array.isArray(raw)) return raw.map(String);
  if (typeof raw === "string") return [raw];
  return [];
}

type FilterKey = "all" | "docs_append" | "gmail_draft" | "audited";

export default function ApprovalsPage() {
  const [actions, setActions] = useState<ApprovalAction[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterKey>("all");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    const list = await getApprovals();
    // Publish gate only — reply approve/reject lives on Queue.
    setActions(
      list.filter((a) => a.type === "docs_append" || a.type === "gmail_draft"),
    );
  }, []);

  useEffect(() => {
    refresh().catch((err: Error) => setError(err.message));
  }, [refresh]);

  const pendingCount = useMemo(
    () => actions.filter((a) => a.status === "pending_approval").length,
    [actions],
  );

  const filtered = useMemo(() => {
    if (filter === "all") return actions;
    if (filter === "audited") {
      return actions.filter((a) => a.status !== "pending_approval");
    }
    return actions.filter((a) => a.type === filter);
  }, [actions, filter]);

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

  const filters: { key: FilterKey; label: string }[] = [
    { key: "all", label: "All pending" },
    { key: "docs_append", label: "Docs" },
    { key: "gmail_draft", label: "Drafts" },
    { key: "audited", label: "Audited" },
  ];

  return (
    <div className="flex w-full flex-col">
      <div className="mb-space-lg flex flex-col gap-space-md">
        <div className="flex flex-col justify-between gap-space-md lg:flex-row lg:items-center">
          <div className="flex flex-col">
            <div className="flex items-center gap-space-sm">
              <h1 className="font-headline-lg text-headline-lg tracking-tight text-on-surface">
                Approvals
              </h1>
              <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-container-high px-2.5 py-0.5 font-code-sm text-code-sm font-semibold uppercase tracking-wider text-on-surface-variant">
                <span className="h-1.5 w-1.5 rounded-full bg-tertiary" />
                Publish gate
              </span>
            </div>
            <p className="mt-1 max-w-4xl font-body-md text-body-md text-on-surface-variant">
              Publish gate for weekly Docs append and Gmail drafts (after Pulse →
              Prepare publish). Support replies are approved on the Queue tab.
            </p>
          </div>
        </div>

        {pendingCount > 0 && (
          <div className="flex items-center justify-between gap-space-md rounded-lg bg-surface-container-high px-space-lg py-3 text-on-surface shadow-sm">
            <div className="flex items-center gap-space-md">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary-container text-on-secondary-container">
                <MaterialIcon name="gavel" className="text-lg" />
              </div>
              <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:gap-space-md">
                <span className="font-headline-sm text-headline-sm font-semibold text-on-surface">
                  {pendingCount} pending action
                  {pendingCount === 1 ? "" : "s"} require human clearance
                </span>
              </div>
            </div>
            <span className="flex-shrink-0 rounded bg-secondary-container px-2 py-0.5 font-code-sm text-code-sm font-semibold text-on-secondary-container">
              HOLD_POLICY: STRICT
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="mb-space-lg">
          <DeckAlert tone="error">{error}</DeckAlert>
        </div>
      )}

      <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
        <div className="flex flex-col gap-space-md lg:col-span-5 xl:col-span-4">
          <div className="flex flex-col gap-space-sm rounded-lg bg-surface-container-lowest p-space-md shadow-sm">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MaterialIcon
                  name="format_list_bulleted"
                  className="text-base text-on-surface-variant"
                />
                <span className="font-headline-sm text-headline-sm font-bold text-on-surface">
                  Gate actions ({filtered.length})
                </span>
              </div>
              <span className="rounded-full bg-surface-container-low px-2 py-0.5 font-code-sm text-code-sm text-on-surface-variant">
                Total: {actions.length}
              </span>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-space-xs">
              {filters.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => setFilter(f.key)}
                  className={`rounded px-2.5 py-1 font-label-sm text-label-sm transition-colors ${
                    filter === f.key
                      ? "bg-secondary-container font-semibold text-on-secondary-container"
                      : "bg-surface-container-low text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-space-sm">
            {filtered.length === 0 && (
              <p className="rounded-lg bg-surface-container-lowest p-space-md font-body-sm text-body-sm text-on-surface-variant shadow-sm">
                No approval actions.
              </p>
            )}
            {filtered.map((a) => {
              const active = selectedId === a.action_id;
              return (
                <button
                  key={a.action_id}
                  type="button"
                  onClick={() => setSelectedId(a.action_id)}
                  className={`relative rounded-lg bg-surface-container-lowest p-space-md text-left shadow-sm transition-all ${
                    active ? "bg-surface-container-low/70" : "hover:bg-surface-container-low"
                  }`}
                >
                  {active && (
                    <span className="absolute bottom-0 left-0 top-0 w-1 rounded-l-lg bg-primary" />
                  )}
                  <div className="mb-2 flex items-start justify-between gap-space-sm">
                    <TypeChip type={a.type} />
                    <StatusBadge status={a.status} />
                  </div>
                  <p className="truncate font-code-sm text-code-sm text-on-surface-variant">
                    {a.action_id}
                  </p>
                </button>
              );
            })}
          </div>
        </div>

        <section className="overflow-hidden rounded-xl bg-surface-container-lowest shadow-sm lg:col-span-7 xl:col-span-8">
          {!selected ? (
            <p className="p-space-lg font-body-sm text-body-sm text-on-surface-variant">
              Select an action to inspect payload.
            </p>
          ) : (
            <div className="flex flex-col">
              <div className="flex flex-wrap items-center justify-between gap-space-sm border-b border-surface-container bg-surface-container-low p-space-lg">
                <div>
                  <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                    {selected.type} · {selected.status.replace(/_/g, " ")}
                  </h2>
                  <p className="mt-1 font-code-sm text-code-sm text-on-surface-variant">
                    {selected.action_id}
                  </p>
                </div>
                <TypeChip type={selected.type} />
              </div>

              <div className="space-y-space-lg p-space-lg">
                <div>
                  <h3 className="font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
                    Destinations
                  </h3>
                  {destinationsOf(selected).length === 0 ? (
                    <p className="mt-1 font-body-sm text-body-sm text-on-surface-variant">
                      None listed in payload.
                    </p>
                  ) : (
                    <ul className="mt-2 list-disc space-y-1 pl-5 font-body-md text-body-md text-on-surface">
                      {destinationsOf(selected).map((d) => (
                        <li key={d}>{d}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div>
                  <h3 className="font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
                    Payload preview
                  </h3>
                  <pre className="mt-2 max-h-80 overflow-auto rounded-lg bg-surface-container-low p-space-md font-code-sm text-code-sm text-on-surface">
                    {JSON.stringify(selected.payload_preview, null, 2)}
                  </pre>
                </div>

                {selected.edited_content && (
                  <div>
                    <h3 className="font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
                      Edited content
                    </h3>
                    <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-surface-container-low p-space-md font-body-md text-body-md text-on-surface">
                      {selected.edited_content}
                    </pre>
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-space-sm border-t border-surface-container bg-surface-container-lowest p-space-lg shadow-deck-sticky">
                <button
                  type="button"
                  onClick={onReject}
                  disabled={busy || selected.status !== "pending_approval"}
                  className="flex items-center gap-1.5 rounded-lg bg-surface-container-low px-space-md py-2 font-label-md text-label-md font-semibold text-error transition-all hover:bg-error-container hover:text-on-error-container disabled:opacity-40"
                >
                  <MaterialIcon name="close" className="text-[17px]" />
                  Reject
                </button>
                <button
                  type="button"
                  onClick={onApprove}
                  disabled={busy || selected.status !== "pending_approval"}
                  className="flex items-center gap-2 rounded-lg bg-primary px-space-xl py-2 font-label-md text-label-md font-semibold text-on-primary shadow-sm transition-all hover:bg-tertiary disabled:opacity-40"
                >
                  <MaterialIcon name="check_circle" className="text-[18px]" />
                  Approve
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function TypeChip({ type }: { type: ApprovalActionType }) {
  return (
    <span className="inline-flex items-center rounded bg-surface-variant px-2 py-0.5 font-code-sm text-code-sm font-semibold tracking-tight text-on-surface">
      {type}
    </span>
  );
}
