import type { Metadata } from "next";
import { SupportDeckShell } from "@/components/support-deck/SupportDeckShell";

export const metadata: Metadata = {
  title: "Support Deck — Operator Console",
  description:
    "Groww Support Deck: queue drafts, weekly pulse, explainers, and gated approvals.",
};

export default function SupportDeckLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return <SupportDeckShell>{children}</SupportDeckShell>;
}
