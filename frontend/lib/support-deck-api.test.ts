/**
 * Node test for Support Deck API client URL building + method paths.
 * Run: npx --yes tsx --test lib/support-deck-api.test.ts
 */
import assert from "node:assert/strict";
import { afterEach, describe, it, mock } from "node:test";
import {
  approveAction,
  findPendingReplyAction,
  getQueue,
  patchQueueDraft,
  rejectAction,
  runWeekly,
  supportDeckApiBase,
  type ApprovalAction,
} from "./support-deck-api";

describe("supportDeckApiBase", () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_SUPPORT_DECK_URL;
  });

  it("defaults to same-origin proxy when env unset", () => {
    delete process.env.NEXT_PUBLIC_SUPPORT_DECK_URL;
    assert.equal(supportDeckApiBase(), "");
  });

  it("strips trailing slash from NEXT_PUBLIC_SUPPORT_DECK_URL", () => {
    process.env.NEXT_PUBLIC_SUPPORT_DECK_URL = "http://localhost:9000/";
    assert.equal(supportDeckApiBase(), "http://localhost:9000");
  });
});

describe("support-deck-api fetch helpers", () => {
  afterEach(() => {
    mock.restoreAll();
    delete process.env.NEXT_PUBLIC_SUPPORT_DECK_URL;
  });

  it("getQueue GETs same-origin /api/support-deck/queue by default", async () => {
    delete process.env.NEXT_PUBLIC_SUPPORT_DECK_URL;
    const calls: { url: string; init?: RequestInit }[] = [];
    mock.method(globalThis, "fetch", async (url: string | URL, init?: RequestInit) => {
      calls.push({ url: String(url), init });
      return new Response(JSON.stringify([{ question_id: "q-1", status: "drafted" }]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    const items = await getQueue();
    assert.equal(calls[0]?.url, "/api/support-deck/queue");
    assert.equal(calls[0]?.init?.method ?? "GET", "GET");
    assert.equal(items[0]?.question_id, "q-1");
  });

  it("patchQueueDraft PATCHes draft body only", async () => {
    process.env.NEXT_PUBLIC_SUPPORT_DECK_URL = "http://sd.test";
    const calls: { url: string; init?: RequestInit }[] = [];
    mock.method(globalThis, "fetch", async (url: string | URL, init?: RequestInit) => {
      calls.push({ url: String(url), init });
      return new Response(
        JSON.stringify({ question_id: "q-1", draft: "edited", status: "drafted" }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    });

    await patchQueueDraft("q-1", "edited");
    assert.equal(calls[0]?.url, "http://sd.test/api/support-deck/queue/q-1");
    assert.equal(calls[0]?.init?.method, "PATCH");
    assert.equal(JSON.parse(String(calls[0]?.init?.body)).draft, "edited");
  });

  it("approveAction and rejectAction hit approval routes", async () => {
    process.env.NEXT_PUBLIC_SUPPORT_DECK_URL = "http://sd.test";
    const urls: string[] = [];
    mock.method(globalThis, "fetch", async (url: string | URL, init?: RequestInit) => {
      urls.push(`${init?.method ?? "GET"} ${String(url)}`);
      return new Response(JSON.stringify({ action_id: "a1", status: "approved" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    await approveAction("a1");
    await rejectAction("a2");
    assert.equal(
      urls[0],
      "POST http://sd.test/api/support-deck/approvals/a1/approve?invoke_mcp=true",
    );
    assert.equal(urls[1], "POST http://sd.test/api/support-deck/approvals/a2/reject");
  });

  it("runWeekly posts live query flag", async () => {
    process.env.NEXT_PUBLIC_SUPPORT_DECK_URL = "http://sd.test";
    const urls: string[] = [];
    mock.method(globalThis, "fetch", async (url: string | URL, init?: RequestInit) => {
      urls.push(`${init?.method ?? "GET"} ${String(url)}`);
      return new Response(JSON.stringify({ actions: [], artifacts: {} }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    });

    await runWeekly(false);
    assert.equal(urls[0], "POST http://sd.test/api/support-deck/weekly/run?live=false");
  });

  it("findPendingReplyAction matches question_id", () => {
    const actions: ApprovalAction[] = [
      {
        action_id: "a-other",
        type: "docs_append",
        payload_preview: {},
        content_hash: "",
        status: "pending_approval",
        edited_content: null,
        created_at: null,
        updated_at: null,
        decided_at: null,
      },
      {
        action_id: "a-reply",
        type: "reply_finalize",
        payload_preview: { question_id: "q-9" },
        content_hash: "",
        status: "pending_approval",
        edited_content: null,
        created_at: null,
        updated_at: null,
        decided_at: null,
      },
    ];
    assert.equal(findPendingReplyAction(actions, "q-9")?.action_id, "a-reply");
    assert.equal(findPendingReplyAction(actions, "missing"), undefined);
  });
});
