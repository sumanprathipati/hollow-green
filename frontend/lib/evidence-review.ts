import type { EvidenceReviewStatus } from "@/lib/types";

export type ReviewSectionKey =
  | "evidence_summary"
  | "deterministic_assessment_explanation"
  | "evidence_gaps"
  | "human_review_checks";

export const REVIEW_SECTION_ORDER: ReviewSectionKey[] = [
  "evidence_summary",
  "deterministic_assessment_explanation",
  "evidence_gaps",
  "human_review_checks",
];

export function reviewSectionTitle(key: ReviewSectionKey, recommendation: string): string {
  switch (key) {
    case "evidence_summary":
      return "What the public evidence shows";
    case "deterministic_assessment_explanation":
      return `Why the deterministic assessment is ${recommendation}`;
    case "evidence_gaps":
      return "Evidence gaps and what cannot be determined";
    case "human_review_checks":
      return "Suggested human review checks";
  }
}

export interface ReviewStatusCopy {
  title: string;
  message: string;
}

export function reviewStatusCopy(status: EvidenceReviewStatus | "rate-limited"): ReviewStatusCopy {
  switch (status) {
    case "unavailable":
      return {
        title: "AI review is not configured",
        message:
          "AI review is not configured. The deterministic assessment and source evidence remain available.",
      };
    case "error":
      return {
        title: "Evidence review failed",
        message:
          "The evidence review could not be generated. The deterministic assessment and source evidence remain available.",
      };
    case "rate-limited":
      return {
        title: "Rate limit exceeded",
        message:
          "The request was rate limited. The deterministic assessment and source evidence remain available.",
      };
    case "blocked":
      return {
        title: "Review withheld",
        message:
          "The AI response did not meet evidence-grounding requirements. Use the deterministic assessment and cited evidence below.",
      };
  }
  return { title: "", message: "" };
}

/** Mirror of the backend forbidden-vocabulary guard, for display-layer tests. */
const BANNED_REVIEW_PHRASES = [
  "proceed with caution",
  "hold / investigate",
  "rollback verified",
  "release approval",
  "deployment approval",
  "production ready",
  "safe to deploy",
  "deploy now",
  "clean_success",
  "recovered_success",
  "fragile_success",
];

const BANNED_REVIEW_WORDS = ["proceed", "failed"];

export function containsBannedReviewLanguage(text: string): boolean {
  const normalized = ` ${text.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()} `;
  for (const phrase of BANNED_REVIEW_PHRASES) {
    const normalizedPhrase = ` ${phrase.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim()} `;
    if (normalized.includes(normalizedPhrase)) return true;
  }
  for (const word of BANNED_REVIEW_WORDS) {
    if (new RegExp(`\\b${word}\\b`).test(text.toLowerCase())) return true;
  }
  return false;
}

/** Regenerate is offered only after a successful review exists. */
export function canRegenerate(status: EvidenceReviewStatus | null): boolean {
  return status === "available";
}
