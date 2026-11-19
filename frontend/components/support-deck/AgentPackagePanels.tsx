"use client";

import type { AgentPackage } from "@/lib/support-deck-api";

function hasPackage(pkg: AgentPackage | null | undefined): boolean {
  return !!pkg && Object.keys(pkg).length > 0;
}

export function AgentPackagePanels({
  pkg,
}: {
  pkg: AgentPackage | null | undefined;
}) {
  if (!hasPackage(pkg)) {
    return (
      <div className="border-t border-surface-container bg-surface-container-low px-space-lg py-space-md">
        <p className="font-body-sm text-body-sm text-on-surface-variant">
          No agent package (legacy item).
        </p>
      </div>
    );
  }

  const data = pkg as AgentPackage;
  const reviewerPass = data.reviewer?.passed === true;
  const routing = data.orchestrator?.routing_note;
  const recurring = data.pattern?.recurring === true;
  const policyCategory = data.policy?.category ?? "factual";

  const routingLine = recurring
    ? `Policy ${policyCategory}. Pattern recurring (count=${data.pattern?.count ?? 0}) — keep ticket visible in dual-loop signal.`
    : `Policy ${policyCategory}. Pattern count=${data.pattern?.count ?? 0} (threshold ${data.pattern?.threshold ?? "—"}).`;

  return (
    <div className="flex flex-col gap-space-md border-t border-surface-container bg-surface-container-low px-space-lg py-space-md">
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={`rounded px-2 py-0.5 font-label-sm text-label-sm font-semibold ${
            reviewerPass
              ? "bg-secondary-container text-on-secondary-container"
              : "bg-error-container text-on-error-container"
          }`}
        >
          REVIEWER {reviewerPass ? "PASS" : "FAIL"}
        </span>
        {routing && (
          <span className="rounded bg-surface-container-lowest px-2 py-0.5 font-code-sm text-code-sm text-on-surface-variant shadow-sm">
            ROUTING: {String(routing).toUpperCase()}
          </span>
        )}
        {data.pattern && (
          <span
            className={`rounded px-2 py-0.5 font-label-sm text-label-sm font-semibold ${
              recurring
                ? "bg-amber-100 text-amber-900"
                : "bg-surface-container text-on-surface-variant"
            }`}
          >
            PATTERN: {recurring ? "RECURRING" : "NEW"}
          </span>
        )}
      </div>

      <div className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm">
        <h3 className="mb-1 font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
          Internal routing note
        </h3>
        <p className="font-code-sm text-code-sm text-on-surface">
          routing_note={data.orchestrator?.routing_note ?? "—"} · status=
          {data.orchestrator?.status ?? "—"}
        </p>
        <p className="mt-1 font-body-sm text-body-sm text-on-surface-variant">
          {routingLine}
        </p>
      </div>

      <div className="grid gap-space-sm md:grid-cols-3">
        <section className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm">
          <h3 className="mb-2 font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
            Retrieve
          </h3>
          <p className="font-code-sm text-code-sm text-on-surface">
            path={data.retrieve?.path ?? "—"} · chunks=
            {data.retrieve?.chunk_count ?? 0}
          </p>
          {(data.retrieve?.source_urls?.length ?? 0) > 0 && (
            <ul className="mt-2 space-y-1 font-code-sm text-code-sm text-primary">
              {(data.retrieve?.source_urls ?? []).slice(0, 3).map((url) => (
                <li key={url} className="truncate">
                  <a href={url} target="_blank" rel="noreferrer" className="hover:underline">
                    {url}
                  </a>
                </li>
              ))}
            </ul>
          )}
          {(data.retrieve?.searched?.length ?? 0) > 0 && (
            <div className="mt-2 space-y-0.5 font-code-sm text-code-sm text-on-surface-variant">
              {(data.retrieve?.searched ?? []).slice(0, 4).map((s, i) => (
                <div key={`${i}-${s}`} className="truncate">
                  {s}
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm">
          <h3 className="mb-2 font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
            Pattern
          </h3>
          <p className="font-code-sm text-code-sm text-on-surface">
            {data.pattern?.normalized_text || "—"}
            {recurring ? " (recurring)" : ""}
          </p>
          <p className="mt-1 font-code-sm text-code-sm text-on-surface-variant">
            lifetime_count={data.pattern?.count ?? 0} · threshold=
            {data.pattern?.threshold ?? "—"}
          </p>
          {(data.pattern?.window_start || data.pattern?.window_end) && (
            <p className="mt-1 font-code-sm text-code-sm text-on-surface-variant">
              {data.pattern?.window_start ?? "—"} → {data.pattern?.window_end ?? "—"}
            </p>
          )}
        </section>

        <section className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm">
          <h3 className="mb-2 font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
            Policy
          </h3>
          <p className="font-code-sm text-code-sm text-on-surface">
            {data.policy?.refuse ? "refuse" : "allow"} · category=
            {data.policy?.category ?? "—"}
          </p>
          {(data.policy?.reasons?.length ?? 0) > 0 && (
            <ul className="mt-2 list-inside list-disc font-body-sm text-body-sm text-on-surface-variant">
              {(data.policy?.reasons ?? []).map((r, i) => (
                <li key={`${i}-${r}`}>{r}</li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <div className="grid gap-space-sm md:grid-cols-2">
        <section className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm">
          <h3 className="mb-1 font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
            Reviewer
          </h3>
          <p className="font-code-sm text-code-sm text-on-surface">
            status={reviewerPass ? "pass" : "fail"} · round=
            {data.reviewer?.round ?? 1}
          </p>
          {(data.reviewer?.flags?.length ?? 0) > 0 && (
            <p className="mt-1 font-code-sm text-code-sm text-amber-900">
              flags: {(data.reviewer?.flags ?? []).join(", ")}
            </p>
          )}
        </section>
        <section className="rounded-lg bg-surface-container-lowest p-space-md shadow-sm">
          <h3 className="mb-1 font-label-sm text-label-sm font-bold uppercase tracking-wider text-on-surface-variant">
            Agents fired
          </h3>
          <p className="font-code-sm text-code-sm text-on-surface">
            fired=[{(data.agents_fired ?? []).join(", ")}]
          </p>
        </section>
      </div>
    </div>
  );
}
