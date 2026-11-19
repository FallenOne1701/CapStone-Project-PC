"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { DeckAlert } from "@/components/support-deck/DeckAlert";
import { MaterialIcon } from "@/components/support-deck/MaterialIcon";
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
    <div className="flex w-full flex-col">
      <div className="mb-space-lg flex flex-col justify-between gap-space-md lg:flex-row lg:items-center">
        <div className="flex flex-col gap-0.5">
          <div className="flex items-center gap-space-sm">
            <h1 className="font-headline-lg text-headline-lg font-bold tracking-tight text-on-surface">
              Pulse
            </h1>
            {pulse && (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-secondary-container px-2 py-0.5 font-label-sm text-label-sm font-semibold text-on-secondary-container">
                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                {pulse.live ? "LIVE" : "SAMPLE"}
              </span>
            )}
          </div>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Weekly Play-store review themes, review traces, and gated publish
            preparation.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-space-md rounded-xl bg-surface-container-lowest p-2 shadow-sm sm:flex-nowrap">
          <label className="flex cursor-pointer select-none items-center gap-space-sm rounded px-space-sm py-1 transition-colors hover:bg-surface-container-low">
            <input
              type="checkbox"
              checked={live}
              onChange={(e) => setLive(e.target.checked)}
              className="h-4 w-4 cursor-pointer rounded accent-primary"
            />
            <span className="flex flex-col">
              <span className="flex items-center gap-1.5 font-label-md text-label-md font-semibold text-on-surface">
                Live Play ingest
                {live && (
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-primary-fixed-dim" />
                )}
              </span>
              <span className="font-code-sm text-code-sm text-on-surface-variant">
                uses pulse --live when checked
              </span>
            </span>
          </label>
          <div className="hidden h-6 w-px bg-surface-container sm:block" />
          <button
            type="button"
            onClick={onPreparePublish}
            disabled={busy}
            className="flex items-center gap-space-sm rounded-lg bg-primary px-4 py-2 font-label-md text-label-md font-semibold text-on-primary shadow-sm transition-all hover:bg-on-tertiary-fixed-variant active:translate-y-px disabled:opacity-50"
          >
            <MaterialIcon name="send_and_archive" className="text-base" />
            {busy ? "Running…" : "Prepare publish"}
          </button>
        </div>
      </div>

      <p className="mb-space-lg flex items-center gap-1.5 px-1 font-body-sm text-body-sm text-on-surface-variant">
        <MaterialIcon name="verified" className="text-sm text-primary" />
        Themes, window, review-id traces; Prepare publish creates pending
        approvals in the human gate.
      </p>

      {error && (
        <div className="mb-space-lg">
          <DeckAlert tone="warn">{error}</DeckAlert>
        </div>
      )}

      {pendingActions.length > 0 && (
        <div className="mb-space-lg flex flex-col justify-between gap-space-md rounded-xl bg-secondary-container/70 p-3.5 shadow-sm sm:flex-row sm:items-center">
          <div className="flex items-center gap-space-md">
            <div className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-primary text-on-primary">
              <MaterialIcon name="check" className="text-sm" />
            </div>
            <div className="flex flex-col gap-1 text-on-secondary-container sm:flex-row sm:items-center sm:gap-2">
              <span className="font-label-md text-label-md font-semibold">
                Stage gate initialized:
              </span>
              <span className="font-body-md text-body-md font-medium text-on-surface">
                Created {pendingActions.length} pending action
                {pendingActions.length === 1 ? "" : "s"}.
              </span>
            </div>
          </div>
          <Link
            href="/support-deck/approvals"
            className="inline-flex items-center gap-1 whitespace-nowrap pl-9 font-label-md text-label-md font-bold text-on-secondary-container transition-colors hover:text-on-tertiary-fixed-variant sm:pl-0"
          >
            Open Approvals
            <MaterialIcon name="arrow_forward" className="text-sm" />
          </Link>
        </div>
      )}

      {pulse && (
        <>
          <div className="mb-space-xl grid grid-cols-1 gap-space-md md:grid-cols-3">
            <MetaCard
              icon="calendar_today"
              label="Window"
              value={`${pulse.window_start} → ${pulse.window_end}`}
            />
            <MetaCard
              icon="travel_explore"
              label="Lookback"
              value={`${pulse.lookback_weeks} weeks`}
            />
            <MetaCard
              icon="filter_alt"
              label="Mode"
              value={pulse.live ? "Live ingest" : "Sample"}
            />
          </div>

          <div className="grid grid-cols-1 items-start gap-space-xl xl:grid-cols-12">
            <div className="flex flex-col gap-space-lg xl:col-span-7">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-space-sm">
                  <h2 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                    Identified review themes
                  </h2>
                  <span className="rounded-full bg-surface-container px-2 py-0.5 font-code-sm text-code-sm font-semibold text-on-surface-variant">
                    {themes.length}
                  </span>
                </div>
              </div>

              {themes.length === 0 ? (
                <p className="rounded-xl bg-surface-container-lowest p-space-lg font-body-sm text-body-sm text-on-surface-variant shadow-sm">
                  No themes in latest pulse.
                </p>
              ) : (
                themes.map((t, idx) => (
                  <article
                    key={t.theme_id ?? idx}
                    className="relative flex flex-col gap-space-md overflow-hidden rounded-xl bg-surface-container-lowest p-space-lg shadow-sm"
                  >
                    {idx === 0 && (
                      <span className="absolute bottom-0 left-0 top-0 w-1.5 bg-primary" />
                    )}
                    <div className="flex flex-wrap items-center justify-between gap-space-sm">
                      <div className="flex flex-wrap items-center gap-space-sm">
                        {idx === 0 && (
                          <span className="rounded bg-secondary-container px-2 py-0.5 font-label-sm text-label-sm font-bold text-primary">
                            THEME {String(idx + 1).padStart(2, "0")} · TOP DRIVER
                          </span>
                        )}
                        <h3 className="font-headline-sm text-headline-sm font-bold text-on-surface">
                          {t.label ?? t.theme_id ?? `Theme ${idx + 1}`}
                        </h3>
                      </div>
                      {typeof t.count === "number" && (
                        <span className="rounded bg-error-container px-2.5 py-1 font-code-sm text-code-sm font-bold text-on-error-container">
                          {t.count} reviews
                        </span>
                      )}
                    </div>
                    {t.review_ids && t.review_ids.length > 0 && (
                      <div className="flex flex-wrap items-center gap-space-xs rounded-lg bg-surface-container-low px-3 py-1.5 font-code-sm text-code-sm text-on-surface-variant">
                        <span className="font-label-sm text-label-sm font-semibold text-on-surface">
                          Review traces:
                        </span>
                        {t.review_ids.join(", ")}
                      </div>
                    )}
                    {t.quotes && t.quotes.length > 0 && (
                      <ul className="space-y-1.5">
                        {t.quotes.map((q, i) => (
                          <li
                            key={i}
                            className="border-l-2 border-primary/30 pl-3 font-body-md text-body-md italic text-on-surface"
                          >
                            “{q}”
                          </li>
                        ))}
                      </ul>
                    )}
                  </article>
                ))
              )}
            </div>

            <div className="xl:col-span-5">
              <section className="rounded-xl bg-surface-container-lowest p-space-lg shadow-sm">
                <h2 className="mb-space-md font-headline-sm text-headline-sm font-bold text-on-surface">
                  Pulse markdown
                </h2>
                <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-lg bg-surface-container-low p-space-md font-code-sm text-code-sm text-on-surface">
                  {pulse.pulse_markdown || "(empty)"}
                </pre>
              </section>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function MetaCard({
  icon,
  label,
  value,
}: {
  icon: string;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-center gap-space-md rounded-xl bg-surface-container-lowest p-space-md shadow-sm">
      <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-surface-container-low text-primary">
        <MaterialIcon name={icon} className="text-lg" />
      </div>
      <div className="flex min-w-0 flex-col">
        <span className="font-label-sm text-label-sm font-semibold uppercase tracking-wider text-on-surface-variant">
          {label}
        </span>
        <span className="truncate font-body-md text-body-md font-bold text-on-surface">
          {value}
        </span>
      </div>
    </div>
  );
}
