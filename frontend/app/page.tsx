import { AppHeader } from "@/components/AppHeader";
import { ChatPanel } from "@/components/ChatPanel";
import { DisclaimerBanner } from "@/components/DisclaimerBanner";
import { SchemesSidebar } from "@/components/SchemesSidebar";

export default function HomePage() {
  return (
    <div className="flex min-h-screen flex-col selection:bg-brand-100 selection:text-brand-900">
      <AppHeader />
      <DisclaimerBanner />
      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col items-start justify-center gap-8 px-4 py-6 sm:px-6 lg:flex-row">
        <ChatPanel />
        <SchemesSidebar />
      </main>
    </div>
  );
}
