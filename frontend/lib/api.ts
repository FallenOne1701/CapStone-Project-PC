import type { AskResponse } from "./types";

/** Same-origin proxy → Railway (avoids browser CORS / localhost fallback). */
const ASK_PATH = "/api/ask";

export async function askQuestion(question: string): Promise<AskResponse> {
  const res = await fetch(ASK_PATH, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }

  return (await res.json()) as AskResponse;
}
