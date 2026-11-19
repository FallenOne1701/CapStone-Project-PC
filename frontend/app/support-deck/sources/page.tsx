"use client";

import { useEffect, useMemo, useState } from "react";
import { DeckAlert } from "@/components/support-deck/DeckAlert";
import { MaterialIcon } from "@/components/support-deck/MaterialIcon";
import { getSources, type SourceClaim } from "@/lib/support-deck-api";

export default function SourcesPage() {
  const [claims, setClaims] = useState<SourceClaim[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    getSources()
      .then(setClaims)
      .catch((err: Error) => setError(err.message));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return claims;
    return claims.filter((c) => {
      const hay = `${c.claim} ${c.url} ${c.last_checked} ${c.explainer_id ?? ""}`.toLowerCase();
      return hay.includes(q);
    });
  }, [claims, query]);

  const withUrl = claims.filter((c) => c.url).length;

  return (
    <div className="flex w-full flex-col">
      <div className="mb-space-lg flex flex-col justify-between gap-space-md lg:flex-row lg:items-end">
        <div>
          <h1 className="font-headline-lg text-headline-lg font-bold tracking-tight text-on-surface">
            Sources
          </h1>
          <p className="mt-1 font-body-md text-body-md text-on-surface-variant">
            Read-only audit: claim → URL + last-checked.
          </p>
        </div>
        <div className="flex flex-wrap gap-space-sm">
          <span className="rounded-lg bg-surface-container-lowest px-3 py-1.5 font-code-sm text-code-sm text-on-surface shadow-sm">
            claims: {claims.length}
          </span>
          <span className="rounded-lg bg-surface-container-lowest px-3 py-1.5 font-code-sm text-code-sm text-on-surface shadow-sm">
            with URL: {withUrl}
          </span>
        </div>
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
          placeholder="Filter claims or URLs…"
          className="w-full rounded-lg bg-surface-container-lowest py-1.5 pl-9 pr-4 font-body-md text-body-md text-on-surface shadow-sm placeholder:text-on-surface-variant/60 focus:outline-none focus:ring-1 focus:ring-primary"
        />
      </div>

      {error && (
        <div className="mb-space-lg">
          <DeckAlert tone="error">{error}</DeckAlert>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl bg-surface-container-lowest shadow-sm">
        <table className="w-full border-collapse text-left">
          <thead className="border-b border-surface-container bg-surface-container-low">
            <tr>
              <th className="px-space-lg py-3 font-label-sm text-label-sm font-semibold uppercase tracking-wider text-on-surface-variant">
                Claim
              </th>
              <th className="px-space-lg py-3 font-label-sm text-label-sm font-semibold uppercase tracking-wider text-on-surface-variant">
                URL
              </th>
              <th className="px-space-lg py-3 font-label-sm text-label-sm font-semibold uppercase tracking-wider text-on-surface-variant">
                Last checked
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-container">
            {filtered.length === 0 && !error && (
              <tr>
                <td
                  colSpan={3}
                  className="px-space-lg py-8 font-body-sm text-body-sm text-on-surface-variant"
                >
                  No source claims yet.
                </td>
              </tr>
            )}
            {filtered.map((c, i) => (
              <tr
                key={`${c.url}-${i}`}
                className="transition-colors hover:bg-surface-container-low/60"
              >
                <td className="max-w-md px-space-lg py-3 font-body-md text-body-md text-on-surface">
                  {c.claim}
                  {c.explainer_id && (
                    <span className="mt-1 block font-code-sm text-code-sm text-on-surface-variant">
                      explainer: {c.explainer_id}
                    </span>
                  )}
                </td>
                <td className="px-space-lg py-3">
                  {c.url ? (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex max-w-md items-center gap-1 break-all font-code-sm text-code-sm text-primary hover:underline"
                    >
                      {c.url}
                      <MaterialIcon name="open_in_new" className="flex-shrink-0 text-xs" />
                    </a>
                  ) : (
                    <span className="text-on-surface-variant">—</span>
                  )}
                </td>
                <td className="whitespace-nowrap px-space-lg py-3 font-code-sm text-code-sm text-on-surface-variant">
                  {c.last_checked}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
