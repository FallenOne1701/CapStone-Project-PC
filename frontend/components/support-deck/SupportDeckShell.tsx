"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/support-deck/queue", label: "Queue" },
  { href: "/support-deck/pulse", label: "Pulse" },
  { href: "/support-deck/explainers", label: "Explainers" },
  { href: "/support-deck/approvals", label: "Approvals" },
  { href: "/support-deck/sources", label: "Sources" },
] as const;

export function SupportDeckShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex items-center gap-3">
            <Link
              href="/support-deck/queue"
              className="text-base font-bold tracking-tight text-brand-900"
            >
              Support Deck
            </Link>
            <span className="hidden text-xs font-medium text-slate-500 sm:inline">
              Operator console · dual loops + approval gate
            </span>
          </div>
          <Link
            href="/"
            className="text-sm font-medium text-slate-600 underline-offset-2 hover:text-brand-800 hover:underline"
          >
            FAQ Assistant
          </Link>
        </div>
        <nav
          className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4 pb-2 sm:px-6"
          aria-label="Support Deck views"
        >
          {NAV.map((item) => {
            const active = pathname === item.href || pathname.startsWith(item.href + "/");
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-semibold transition-colors ${
                  active
                    ? "bg-brand-100 text-brand-900"
                    : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6">{children}</main>
    </div>
  );
}
