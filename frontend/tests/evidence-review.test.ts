import { describe, expect, it } from "vitest";
import {
  REVIEW_SECTION_ORDER,
  canRegenerate,
  containsBannedReviewLanguage,
  reviewSectionTitle,
  reviewStatusCopy,
} from "@/lib/evidence-review";

describe("review section titles", () => {
  it("covers all four fixed sections", () => {
    expect(REVIEW_SECTION_ORDER).toEqual([
      "evidence_summary",
      "deterministic_assessment_explanation",
      "evidence_gaps",
      "human_review_checks",
    ]);
  });

  it("names the deterministic recommendation in section two", () => {
    expect(reviewSectionTitle("evidence_summary", "X")).toBe("What the public evidence shows");
    expect(
      reviewSectionTitle("deterministic_assessment_explanation", "ELEVATED CHANGE RISK — INVESTIGATE"),
    ).toBe("Why the deterministic assessment is ELEVATED CHANGE RISK — INVESTIGATE");
    expect(reviewSectionTitle("evidence_gaps", "X")).toBe(
      "Evidence gaps and what cannot be determined",
    );
    expect(reviewSectionTitle("human_review_checks", "X")).toBe("Suggested human review checks");
  });
});

describe("review status copy", () => {
  it("explains unavailable without alarming", () => {
    const copy = reviewStatusCopy("unavailable");
    expect(copy.message).toContain("not configured");
    expect(copy.message).toContain("deterministic assessment");
  });

  it("keeps blocked content hidden by wording", () => {
    const copy = reviewStatusCopy("blocked");
    expect(copy.message).toContain("grounding");
  });

  it("covers error and rate-limited states", () => {
    expect(reviewStatusCopy("error").message).toContain("deterministic assessment");
    expect(reviewStatusCopy("rate-limited").title).toContain("Rate limit");
  });
});

describe("regenerate gating", () => {
  it("offers regenerate only after success", () => {
    expect(canRegenerate("available")).toBe(true);
    expect(canRegenerate(null)).toBe(false);
    expect(canRegenerate("blocked")).toBe(false);
    expect(canRegenerate("unavailable")).toBe(false);
    expect(canRegenerate("error")).toBe(false);
  });
});

describe("banned review language", () => {
  it("flags deployment-approval wording", () => {
    for (const bad of [
      "You may proceed after review.",
      "PROCEED WITH CAUTION here.",
      "We grant deployment approval.",
      "Classification looks like clean_success.",
      "It is safe to deploy now.",
      "The release failed last night.",
    ]) {
      expect(containsBannedReviewLanguage(bad)).toBe(true);
    }
  });

  it("passes ordinary review prose", () => {
    for (const good of [
      "Three recent commits are recorded.",
      "Confirm CI status in the internal system.",
      "No public evidence was available for health status.",
      "The deterministic result is elevated change risk.",
    ]) {
      expect(containsBannedReviewLanguage(good)).toBe(false);
    }
  });
});
