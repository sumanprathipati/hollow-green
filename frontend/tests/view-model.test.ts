import { describe, expect, it } from "vitest";
import type { ReleaseLog, ReleaseReport } from "@/lib/types";
import {
  deductionRows,
  evidenceUrlForEvent,
  followUpRows,
  scoreCards,
  sortedEvents,
} from "@/lib/view-model";

function sampleReport(): ReleaseReport {
  return {
    release_id: "rel-fragile-003",
    classification: "fragile_success",
    terminal: "succeeded",
    score: {
      reserve_level: 23,
      recovery_load: "critical",
      deductions: [
        { rule_id: "retry.consume", event_ids: ["evt-02"], points: 42, reason: "retries" },
        { rule_id: "manual.consume", event_ids: ["evt-06"], points: 20, reason: "manual" },
      ],
      buffers: {
        retries_used: 4,
        retries_left: 1,
        retry_reserve_pct: 20,
        time_remaining_original_pct: 16.7,
        time_remaining_effective_pct: 16.7,
        extension_total_min: 0,
        rollback_available: true,
        rollback_fresh: true,
        health_end: "pass",
        manual_count: 1,
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
      level: "critical",
      retries_left: 1,
      can_survive_second_failure: false,
      rationale: ["reserve 23 < 25"],
    },
  };
}

describe("scoreCards", () => {
  it("maps report to five card rows", () => {
    const rows = scoreCards(sampleReport());
    expect(rows.map((r) => r.label)).toEqual([
      "Classification",
      "Reserve Level",
      "Recovery Load",
      "Retries left",
      "Second-failure tolerance",
    ]);
    expect(rows[1].value).toBe("23");
  });
});

describe("sortedEvents", () => {
  it("sorts by timestamp then event_id", () => {
    const events = [
      { event_id: "evt-02", release_id: "r", ts: "2026-01-01T00:20:00+00:00", type: "b", actor: "system" },
      { event_id: "evt-01", release_id: "r", ts: "2026-01-01T00:00:00+00:00", type: "a", actor: "system" },
    ];
    expect(sortedEvents(events).map((e) => e.event_id)).toEqual(["evt-01", "evt-02"]);
  });

  it("handles empty list", () => {
    expect(sortedEvents([])).toEqual([]);
  });
});

describe("deduction and follow-up rows", () => {
  it("preserves rule_id/points/reason/event_ids", () => {
    const rows = deductionRows(sampleReport());
    expect(rows[0].rule_id).toBe("retry.consume");
    expect(rows[0].event_ids).toEqual(["evt-02"]);
  });

  it("preserves severity/event_ids/required_action", () => {
    const rows = followUpRows(sampleReport());
    expect(rows[0].severity).toBe("low");
    expect(rows[0].required_action).toBe("Reduce flakiness");
  });

  it("passes all 10 buffer fields through", () => {
    const buffers = sampleReport().score.buffers;
    expect(Object.keys(buffers)).toHaveLength(10);
    expect(buffers.retries_left).toBe(1);
  });
});

describe("evidenceUrlForEvent", () => {
  function log(): ReleaseLog {
    return {
      schema_version: "1.0",
      release_id: "r",
      service: "s",
      window_minutes: 60,
      retry_budget_max: 5,
      events: [
        {
          event_id: "evt-01",
          release_id: "r",
          ts: "2026-01-01T00:00:00+00:00",
          type: "deploy_started",
          actor: "system",
          details: { source_url: "https://github.com/o/r" },
        },
        {
          event_id: "evt-02",
          release_id: "r",
          ts: "2026-01-01T00:01:00+00:00",
          type: "deploy_progress",
          actor: "system",
          details: {},
        },
      ],
    };
  }

  it("returns the source URL when recorded", () => {
    expect(evidenceUrlForEvent(log(), "evt-01")).toBe("https://github.com/o/r");
  });

  it("returns null when unavailable", () => {
    expect(evidenceUrlForEvent(log(), "evt-02")).toBeNull();
    expect(evidenceUrlForEvent(log(), "evt-99")).toBeNull();
  });
});
