import { describe, expect, it } from "vitest";
import {
  buildDecisionBrief,
  buildPublicDecisionBrief,
  getRecommendation,
  getRiskDrivers,
  toneForChangeRisk,
  toneForCompleteness,
  toneForDecision,
  toneForRecoveryLoad,
  toneForSeverity,
  toneForTolerance,
} from "@/lib/decision";
import type { PublicDataAssessment, ReleaseLog, ReleaseReport } from "@/lib/types";

function report(): ReleaseReport {
  return {
    release_id: "rel-recovered-002",
    classification: "recovered_success",
    terminal: "succeeded",
    score: {
      reserve_level: 82,
      recovery_load: "low",
      deductions: [
        { rule_id: "retry.consume", event_ids: ["evt-02", "evt-04"], points: 18, reason: "retries" },
      ],
      buffers: {
        retries_used: 2,
        retries_left: 3,
        retry_reserve_pct: 60,
        time_remaining_original_pct: 50,
        time_remaining_effective_pct: 50,
        extension_total_min: 0,
        rollback_available: true,
        rollback_fresh: true,
        health_end: "pass",
        manual_count: 0,
      },
    },
    follow_ups: [
      {
        follow_up_id: "fu-evt-02",
        kind: "retry",
        event_ids: ["evt-02"],
        severity: "low",
        required_action: "Reduce flakiness",
        status: "open",
      },
    ],
    rollback_summary: { executed: false, event_ids: [], verified: false, manual: false },
    tolerance: {
      level: "high",
      retries_left: 3,
      can_survive_second_failure: true,
      rationale: ["reserve 82 >= 70"],
    },
  };
}

function log(): ReleaseLog {
  return {
    schema_version: "1.0",
    release_id: "rel-recovered-002",
    service: "checkout-api-synth",
    window_minutes: 60,
    retry_budget_max: 5,
    events: [
      { event_id: "evt-01", release_id: "rel-recovered-002", ts: "2026-01-01T00:00:00+00:00", type: "deploy_started", actor: "system" },
    ],
  };
}

describe("recommendation mapping", () => {
  it("maps all five classifications", () => {
    expect(getRecommendation("clean_success").decision).toBe("PROCEED");
    expect(getRecommendation("recovered_success").decision).toBe("PROCEED WITH CAUTION");
    expect(getRecommendation("fragile_success").decision).toBe("PROCEED WITH CAUTION");
    expect(getRecommendation("rollback").decision).toBe("ROLLBACK VERIFIED");
    expect(getRecommendation("failed").decision).toBe("HOLD / INVESTIGATE");
  });

  it("assigns tones without color-only reliance", () => {
    expect(getRecommendation("clean_success").tone).toBe("proceed");
    expect(getRecommendation("failed").tone).toBe("hold");
    expect(toneForDecision("proceed")).toBe("emerald");
    expect(toneForDecision("hold")).toBe("red");
  });
});

describe("status tones", () => {
  it("maps recovery load", () => {
    expect(toneForRecoveryLoad("low")).toBe("emerald");
    expect(toneForRecoveryLoad("critical")).toBe("red");
  });

  it("maps tolerance and severity", () => {
    expect(toneForTolerance("high")).toBe("emerald");
    expect(toneForTolerance("critical")).toBe("red");
    expect(toneForSeverity("low")).toBe("emerald");
    expect(toneForSeverity("critical")).toBe("red");
  });
});

describe("risk drivers and brief", () => {
  it("orders drivers by points desc", () => {
    const r = report();
    r.score.deductions = [
      { rule_id: "a", event_ids: ["e1"], points: 10, reason: "a" },
      { rule_id: "b", event_ids: ["e2"], points: 25, reason: "b" },
    ];
    expect(getRiskDrivers(r, 5).map((d) => d.rule_id)).toEqual(["b", "a"]);
  });

  it("brief contains decision, score, drivers, readiness, follow-ups, evidence", () => {
    const brief = buildDecisionBrief(report(), log(), "2026-01-01 00:20:00 UTC");
    expect(brief).toContain("Release Decision Brief");
    expect(brief).toContain("PROCEED WITH CAUTION");
    expect(brief).toContain("82 / 100");
    expect(brief).toContain("retry.consume");
    expect(brief).toContain("can survive");
    expect(brief).toContain("Reduce flakiness");
    expect(brief).toContain("evt-01");
  });
});

describe("public decision brief", () => {
  function assessment(): PublicDataAssessment {
    return {
      data_source: "public-github",
      served_from: "fixture",
      repo_full_name: "octocat/Hello-World",
      candidate: {
        candidate_id: "v1-0",
        kind: "release",
        name: "First release",
        published_at: "2026-01-15T12:00:00+00:00",
        url: "https://github.com/octocat/Hello-World/releases/tag/v1.0",
      },
      retrieved_at: "2026-01-20T00:00:00+00:00",
      source_urls: ["https://api.github.com/repos/octocat/Hello-World"],
      limitations: ["Public repository evidence only — deployment readiness cannot be determined."],
      unavailable_signals: ["health", "rollback"],
      disclaimer: "Public repository evidence only — not a production deployment decision.",
      public_result: {
        change_risk_level: "elevated",
        evidence_completeness: "sufficient",
        deployment_readiness: "not_assessable_from_public_data",
        public_recommendation: "ELEVATED CHANGE RISK — INVESTIGATE",
        reasons: ["candidate: release 'First release'", "observed commits: 3"],
      },
      evidence: {
        repo_full_name: "octocat/Hello-World",
        repo_url: "https://github.com/octocat/Hello-World",
        default_branch: "master",
        stars: 100,
        open_issues_count: 2,
        candidate: {
          candidate_id: "v1-0",
          kind: "release",
          name: "First release",
          published_at: "2026-01-15T12:00:00+00:00",
          url: "https://github.com/octocat/Hello-World/releases/tag/v1.0",
        },
        candidates_available: [],
        commits_recent: [
          {
            sha: "aaa111",
            message: "Initial commit",
            date: "2026-01-10T10:00:00+00:00",
            url: "https://github.com/octocat/Hello-World/commit/aaa111",
          },
        ],
        pulls_recent: [],
        issues_open_sample: [],
        retrieved_at: "2026-01-20T00:00:00+00:00",
        source_urls: ["https://api.github.com/repos/octocat/Hello-World"],
      },
    };
  }

  it("includes disclaimer, sources, limitations, unavailable signals", () => {
    const brief = buildPublicDecisionBrief(assessment(), "2026-01-20 00:00:00 UTC");
    expect(brief).toContain("deployment readiness cannot be determined");
    expect(brief).toContain("octocat/Hello-World");
    expect(brief).toContain("served_from=fixture");
    expect(brief).toContain("https://api.github.com/repos/octocat/Hello-World");
    expect(brief).toContain("Unavailable signals: health, rollback");
  });

  it("uses public vocabulary, never deployment-approval wording", () => {
    const brief = buildPublicDecisionBrief(assessment(), "2026-01-20 00:00:00 UTC");
    expect(brief).toContain("ELEVATED CHANGE RISK — INVESTIGATE");
    for (const banned of [
      "PROCEED",
      "ROLLBACK VERIFIED",
      "HOLD / INVESTIGATE",
      "clean_success",
      "recovered_success",
      "fragile_success",
    ]) {
      expect(brief).not.toContain(banned);
    }
    expect(brief).not.toMatch(/"failed"/);
  });

  it("maps risk and completeness tones", () => {
    expect(toneForChangeRisk("low")).toBe("emerald");
    expect(toneForChangeRisk("elevated")).toBe("red");
    expect(toneForCompleteness("sufficient")).toBe("emerald");
    expect(toneForCompleteness("insufficient")).toBe("slate");
  });
});
