"use client";

import { useEffect, useState } from "react";
import { getSources, type SourceClaim } from "@/lib/support-deck-api";

export default function SourcesPage() {
  const [claims, setClaims] = useState<SourceClaim[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSources()
      .then(setClaims)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl font-bold text-slate-900">Sources</h1>
        <p className="mt-1 text-sm text-slate-600">
          Read-only audit: claim → URL + last-checked.
        </p>
      </header>

      {error && (
        <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
          {error}
        </p>
      )}

      <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-4 py-2">Claim</th>
              <th className="px-4 py-2">URL</th>
              <th className="px-4 py-2">Last checked</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {claims.length === 0 && !error && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-slate-500">
                  No source claims yet.
                </td>
              </tr>
            )}
            {claims.map((c, i) => (
              <tr key={`${c.url}-${i}`}>
                <td className="max-w-md px-4 py-3 text-slate-800">{c.claim}</td>
                <td className="px-4 py-3">
                  {c.url ? (
                    <a
                      href={c.url}
                      target="_blank"
                      rel="noreferrer"
                      className="break-all text-brand-800 underline"
                    >
                      {c.url}
                    </a>
                  ) : (
                    <span className="text-slate-400">—</span>
                  )}
                </td>
                <td className="whitespace-nowrap px-4 py-3 font-mono text-xs text-slate-600">
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
