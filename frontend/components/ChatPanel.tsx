"use client";

import { useState } from "react";
import { askQuestion } from "@/lib/api";
import type { ChatTurn } from "@/lib/types";
import { Composer } from "./Composer";
import { FactualAnswer } from "./FactualAnswer";
import { LoadingState } from "./LoadingState";
import { RefusalMessage } from "./RefusalMessage";
import { WelcomeState } from "./WelcomeState";

export function ChatPanel() {
  const [input, setInput] = useState("");
  const [turn, setTurn] = useState<ChatTurn | null>(null);
  const [error, setError] = useState<string | null>(null);
  const loading = turn?.kind === "loading";

  async function submit(question: string) {
    const q = question.trim();
    if (!q || loading) return;
    setError(null);
    setInput("");
    setTurn({ kind: "loading", text: q });
    try {
      const data = await askQuestion(q);
      if (data.type === "factual") {
        setTurn({ kind: "factual", question: q, data });
      } else {
        setTurn({ kind: "refusal", question: q, data });
      }
    } catch (err) {
      // Keep the asked question visible; don't bounce back to welcome
      // (welcome's compliance blurb looks like a false "refusal").
      setTurn({
        kind: "refusal",
        question: q,
        data: {
          type: "refusal",
          answer:
            err instanceof Error
              ? `Could not answer right now: ${err.message}`
              : "Could not reach the FAQ API. Is the backend running on port 8000?",
          educational_url: "https://www.amfiindia.com/investor-corner/online-centre/onlinecentrelanding",
          reason: "error",
        },
      });
      setError(null);
    }
  }

  return (
    <section className="flex min-h-[calc(100vh-190px)] w-full flex-1 flex-col justify-between overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-sm lg:max-w-[740px]">
      <div className="custom-scrollbar flex flex-1 flex-col justify-start overflow-y-auto p-5 sm:p-7">
        {!turn ? <WelcomeState onExample={submit} /> : null}
        {turn?.kind === "loading" ? (
          <LoadingState question={turn.text} />
        ) : null}
        {turn?.kind === "factual" ? (
          <FactualAnswer question={turn.question} data={turn.data} />
        ) : null}
        {turn?.kind === "refusal" ? (
          <RefusalMessage
            question={turn.question}
            data={turn.data}
            onExample={submit}
          />
        ) : null}
        {error ? (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {error}
          </p>
        ) : null}
      </div>
      <Composer
        value={input}
        disabled={loading}
        onChange={setInput}
        onSubmit={() => submit(input)}
      />
    </section>
  );
}
