"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { DeckAlert } from "@/components/support-deck/DeckAlert";
import { MaterialIcon } from "@/components/support-deck/MaterialIcon";
import { StatusBadge } from "@/components/support-deck/StatusBadge";
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
  const [query, setQuery] = useState("");

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

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return explainers;
    return explainers.filter((ex) => {
      const hay = [
        ex.explainer_id ?? "",
        ...ex.bullets,
        ...ex.links,
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [explainers, query]);

  const activeCount = explainers.filter((e) => e.active).length;
  const totalReuse = [...reuseCounts.values()].reduce((a, b) => a + b, 0);

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
    <div className="flex w-full flex-col">
      <div className="mb-space-xl grid grid-cols-1 gap-gutter md:grid-cols-4">
        <StatCard label="Explainers" value={String(explainers.length)} icon="article" />
        <StatCard label="Active" value={String(activeCount)} icon="check_circle" />
        <StatCard label="Queue reuse" value={String(totalReuse)} icon="replay" />
        <StatCard
          label="Inactive"
          value={String(explainers.length - activeCount)}
          icon="pause_circle"
        />
      </div>

      <div className="mb-space-lg flex flex-col justify-between gap-space-md lg:flex-row lg:items-end">
        <div className="max-w-3xl">
          <h1 className="font-headline-lg text-headline-lg font-bold tracking-tight text-on-surface">
            Explainers
          </h1>
          <p className="mt-1 font-body-md text-body-md text-on-surface-variant">
            Fee explainers are short, cited fact sheets created when the weekly
            Play-review pulse detects fee confusion. Fee-like support questions
            can reuse an active explainer — reuse count shows how often that
            happened in the queue.
          </p>
        </div>
        <button
          type="button"
          onClick={onPreparePublish}
          disabled={busy}
          className="flex items-center gap-space-sm rounded-lg bg-primary px-4 py-2 font-label-md text-label-md font-semibold text-on-primary shadow-sm transition-all hover:bg-tertiary disabled:opacity-50"
        >
          <MaterialIcon name="send_and_archive" className="text-base" />
          {busy ? "Running…" : "Prepare publish"}
        </button>
      </div>

      <div className="relative mb-space-lg max-w-xl">
        <MaterialIcon
          name="search"
          className="absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant"
        />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search explainers by keyword or fee type…"
          className="w-full rounded-lg bg-surface-container-lowest py-1.5 pl-9 pr-4 font-body-md text-body-md text-on-surface shadow-sm placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {error && (
        <div className="mb-space-lg">
          <DeckAlert tone="error">{error}</DeckAlert>
        </div>
      )}

      {pendingActions.length > 0 && (
        <div className="mb-space-lg">
          <DeckAlert tone="ok">
            Created {pendingActions.length} pending action
            {pendingActions.length === 1 ? "" : "s"}.{" "}
            <Link
              href="/support-deck/approvals"
              className="font-semibold underline"
            >
              Open Approvals
            </Link>
          </DeckAlert>
        </div>
      )}

      <div className="space-y-space-lg">
        {filtered.length === 0 && (
          <div className="rounded-xl bg-surface-container-lowest p-space-xl font-body-sm text-body-sm text-on-surface-variant shadow-sm">
            No explainers yet. Run weekly prepare publish or seed via API.
          </div>
        )}
        {filtered.map((ex) => {
          const id = ex.explainer_id ?? "(no id)";
          const reuse = ex.explainer_id
            ? (reuseCounts.get(ex.explainer_id) ?? 0)
            : 0;
          return (
            <article
              key={id}
              className="rounded-xl bg-surface-container-lowest p-space-xl shadow-sm transition-all hover:shadow-md"
            >
              <div className="mb-space-md flex flex-wrap items-center justify-between gap-2">
                <h2 className="font-code-md text-code-md font-bold text-on-surface">
                  {id}
                </h2>
                <div className="flex flex-wrap gap-2">
                  <StatusBadge status={ex.active ? "active" : "inactive"} />
                  <span className="rounded border border-surface-container px-2 py-0.5 font-code-sm text-code-sm font-medium text-on-surface">
                    reuse: {reuse}
                  </span>
                  <span className="rounded border border-surface-container px-2 py-0.5 font-code-sm text-code-sm text-on-surface-variant">
                    last checked: {ex.last_checked}
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-space-xl xl:grid-cols-12">
                <ol className="list-decimal space-y-1.5 pl-5 font-body-md text-body-md text-on-surface xl:col-span-7">
                  {ex.bullets.map((b, i) => (
                    <li key={i}>{b}</li>
                  ))}
                </ol>
                <ul className="space-y-2 xl:col-span-5">
                  <span className="mb-1 block font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
                    Official links
                  </span>
                  {ex.links.map((url) => (
                    <li key={url}>
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-start gap-1 break-all font-code-sm text-code-sm text-primary hover:underline"
                      >
                        <MaterialIcon
                          name="link"
                          className="mt-0.5 flex-shrink-0 text-sm"
                        />
                        {url}
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: string;
  icon: string;
}) {
  return (
    <div className="flex items-center gap-space-md rounded-xl bg-surface-container-lowest p-space-md shadow-sm">
      <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-surface-container-low text-primary">
        <MaterialIcon name={icon} className="text-lg" />
      </div>
      <div className="flex flex-col">
        <span className="font-label-sm text-label-sm font-semibold uppercase tracking-wider text-on-surface-variant">
          {label}
        </span>
        <span className="font-headline-sm text-headline-sm font-bold text-on-surface">
          {value}
        </span>
      </div>
    </div>
  );
}
