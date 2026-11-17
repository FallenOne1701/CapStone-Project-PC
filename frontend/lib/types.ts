export type FactualResponse = {
  type: "factual";
  answer: string;
  citation_url: string;
  last_updated: string;
  scheme_id?: string | null;
};

export type RefusalResponse = {
  type: "refusal";
  answer: string;
  educational_url: string;
  reason: string;
};

export type AskResponse = FactualResponse | RefusalResponse;

export type ChatTurn =
  | { kind: "user"; text: string }
  | { kind: "loading"; text: string }
  | { kind: "factual"; question: string; data: FactualResponse }
  | { kind: "refusal"; question: string; data: RefusalResponse };

export const EXAMPLE_QUESTIONS = [
  "What is the expense ratio of HDFC Large Cap Fund Direct Growth?",
  "What is the exit load for HDFC Mid Cap Fund?",
  "What is the lock-in period for HDFC ELSS Tax Saver Fund?",
] as const;
