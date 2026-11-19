/** Client for Groww Support Deck FastAPI (Task 11 routes). */

export const SUPPORT_DECK_PREFIX = "/api/support-deck";

export type QueueStatus =
  | "pending"
  | "drafted"
  | "approved"
  | "rejected"
  | "not_covered";

export type ApprovalStatus = "pending_approval" | "approved" | "rejected";

export type ApprovalActionType =
  | "docs_append"
  | "gmail_draft"
  | "reply_finalize";

export interface QueueItem {
  question_id: string;
  question_text: string;
  status: QueueStatus;
  draft: string | null;
  citation_url: string | null;
  routing_note: string | null;
  searched: string[];
  reviewer_flags: string[];
  explainer_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ApprovalAction {
  action_id: string;
  type: ApprovalActionType;
  payload_preview: Record<string, unknown>;
  content_hash: string;
  status: ApprovalStatus;
  edited_content: string | null;
  created_at: string | null;
  updated_at: string | null;
  decided_at: string | null;
}

export interface FeeExplainer {
  explainer_id: string | null;
  bullets: string[];
  links: string[];
  last_checked: string;
  active: boolean;
}

export interface SourceClaim {
  claim: string;
  url: string;
  last_checked: string;
  explainer_id?: string | null;
}

export interface PulsePayload {
  themes: unknown;
  top_theme_ids?: string[];
  pulse_markdown: string;
  window_start: string;
  window_end: string;
  lookback_weeks: number;
  live: boolean;
  themes_path?: string;
  pulse_path?: string;
}

export interface WeeklyRunResult {
  artifacts: Record<string, unknown>;
  actions: ApprovalAction[];
  explainer_id: string | null;
}

export function supportDeckApiBase(): string {
  const raw =
    (typeof process !== "undefined" &&
      process.env.NEXT_PUBLIC_SUPPORT_DECK_URL?.trim()) ||
    "http://127.0.0.1:8001";
  return raw.replace(/\/+$/, "");
}

function apiUrl(path: string): string {
  const p = path.startsWith("/") ? path : `/${path}`;
  return `${supportDeckApiBase()}${SUPPORT_DECK_PREFIX}${p}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    let detail = `Support Deck request failed (${res.status})`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // keep status text
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function getQueue(): Promise<QueueItem[]> {
  return request<QueueItem[]>("/queue");
}

export function enqueueQuestion(question: string): Promise<QueueItem> {
  return request<QueueItem>("/queue", {
    method: "POST",
    body: JSON.stringify({ question }),
  });
}

export function patchQueueDraft(
  questionId: string,
  draft: string,
): Promise<QueueItem> {
  return request<QueueItem>(`/queue/${encodeURIComponent(questionId)}`, {
    method: "PATCH",
    body: JSON.stringify({ draft }),
  });
}

export function getPulse(): Promise<PulsePayload> {
  return request<PulsePayload>("/pulse");
}

export function getExplainers(): Promise<FeeExplainer[]> {
  return request<FeeExplainer[]>("/explainers");
}

export function runWeekly(live = false): Promise<WeeklyRunResult> {
  return request<WeeklyRunResult>(`/weekly/run?live=${live ? "true" : "false"}`, {
    method: "POST",
  });
}

export function getApprovals(): Promise<ApprovalAction[]> {
  return request<ApprovalAction[]>("/approvals");
}

export function approveAction(
  actionId: string,
  invokeMcp = false,
): Promise<ApprovalAction> {
  const q = invokeMcp ? "?invoke_mcp=true" : "";
  return request<ApprovalAction>(
    `/approvals/${encodeURIComponent(actionId)}/approve${q}`,
    { method: "POST" },
  );
}

export function rejectAction(actionId: string): Promise<ApprovalAction> {
  return request<ApprovalAction>(
    `/approvals/${encodeURIComponent(actionId)}/reject`,
    { method: "POST" },
  );
}

export function getSources(): Promise<SourceClaim[]> {
  return request<SourceClaim[]>("/sources");
}

/** Find pending reply_finalize for a queue item (payload_preview.question_id). */
export function findPendingReplyAction(
  actions: ApprovalAction[],
  questionId: string,
): ApprovalAction | undefined {
  return actions.find(
    (a) =>
      a.type === "reply_finalize" &&
      a.status === "pending_approval" &&
      a.payload_preview?.question_id === questionId,
  );
}
