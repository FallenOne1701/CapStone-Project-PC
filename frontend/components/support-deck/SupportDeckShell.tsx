"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { getApprovals } from "@/lib/support-deck-api";
import { MaterialIcon } from "./MaterialIcon";

const NAV = [
  { href: "/support-deck/queue", label: "Queue", path: "queue" },
  { href: "/support-deck/pulse", label: "Pulse", path: "pulse" },
  { href: "/support-deck/explainers", label: "Explainers", path: "explainers" },
  { href: "/support-deck/approvals", label: "Approvals", path: "approvals" },
  { href: "/support-deck/sources", label: "Sources", path: "sources" },
] as const;

export function SupportDeckShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [pendingGate, setPendingGate] = useState(0);

  useEffect(() => {
    let cancelled = false;
    getApprovals()
      .then((list) => {
        if (cancelled) return;
        setPendingGate(
          list.filter(
            (a) =>
              a.status === "pending_approval" &&
              (a.type === "docs_append" || a.type === "gmail_draft"),
          ).length,
        );
      })
      .catch(() => {
        if (!cancelled) setPendingGate(0);
      });
    return () => {
      cancelled = true;
    };
  }, [pathname]);

  return (
    <div className="flex min-h-screen flex-col bg-surface font-body-md text-body-md text-on-surface antialiased">
      <header className="fixed left-0 right-0 top-0 z-50 bg-surface-container-lowest shadow-deck">
        <div className="flex h-14 w-full items-center justify-between gap-gutter px-margin-mobile sm:px-margin">
          <div className="flex min-w-0 flex-shrink-0 items-center gap-space-md">
            <Link
              href="/support-deck/queue"
              className="flex items-center gap-space-md"
            >
              <span
                className="flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-primary text-on-primary"
                aria-hidden
              >
                <MaterialIcon name="support_agent" className="text-lg" />
              </span>
              <span className="flex min-w-0 flex-col">
                <span className="flex items-center gap-space-sm">
                  <span className="font-headline-sm text-headline-sm font-bold tracking-tight text-on-surface">
                    Support Deck
                  </span>
                  <span className="hidden items-center gap-1.5 rounded-full bg-secondary-container px-space-sm py-0.5 font-label-sm text-label-sm font-semibold text-on-secondary-container sm:inline-flex">
                    <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
                    DUAL
                  </span>
                </span>
                <span className="hidden font-body-sm text-body-sm font-medium leading-none text-on-surface-variant sm:block">
                  Dual loops · human approval gate
                </span>
              </span>
            </Link>
          </div>

          <nav
            className="hidden items-center gap-space-xs xl:flex"
            aria-label="Support Deck views"
          >
            {NAV.map((item) => {
              const active =
                pathname === item.href || pathname.startsWith(item.href + "/");
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`relative rounded-lg px-space-md py-1.5 font-label-md text-label-md transition-all ${
                    active
                      ? "bg-secondary-container font-semibold text-on-secondary-container"
                      : "text-on-surface-variant hover:bg-surface-container-low hover:text-on-surface"
                  }`}
                >
                  {item.label}
                  {item.path === "approvals" && pendingGate > 0 && (
                    <span className="ml-1.5 inline-flex items-center justify-center rounded-full bg-error-container px-1.5 font-code-sm text-code-sm font-semibold text-on-error-container">
                      {pendingGate}
                    </span>
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="flex flex-shrink-0 items-center gap-space-sm">
            <Link
              href="/"
              className="hidden items-center gap-1.5 rounded-lg px-space-md py-1.5 font-label-md text-label-md text-on-surface-variant transition-colors hover:bg-surface-container-low hover:text-on-surface md:flex"
            >
              <span className="font-medium">FAQ Assistant</span>
              <MaterialIcon name="open_in_new" className="text-sm" />
            </Link>
          </div>
        </div>

        {/* Mobile / laptop nav — Stitch desktop tabs hide below xl */}
        <nav
          className="flex gap-1 overflow-x-auto border-t border-surface-container px-margin-mobile pb-2 pt-1 xl:hidden"
          aria-label="Support Deck views (compact)"
        >
          {NAV.map((item) => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap rounded-lg px-space-md py-1.5 font-label-md text-label-md transition-all ${
                  active
                    ? "bg-secondary-container font-semibold text-on-secondary-container"
                    : "text-on-surface-variant hover:bg-surface-container-low"
                }`}
              >
                {item.label}
                {item.path === "approvals" && pendingGate > 0 ? (
                  <span className="ml-1.5 inline-flex rounded-full bg-error-container px-1.5 font-code-sm text-code-sm font-semibold text-on-error-container">
                    {pendingGate}
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>
      </header>

      <main className="w-full flex-1 bg-surface pt-[7.25rem] xl:pt-14">
        <div className="w-full px-margin-mobile py-margin sm:px-margin">
          {children}
        </div>
      </main>
    </div>
  );
}
