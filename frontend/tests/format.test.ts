import { describe, expect, it } from "vitest";
import { formatRecoveryLoad, formatReserve, formatUtc, formatValidationError } from "@/lib/format";

describe("formatUtc", () => {
  it("formats midnight as 00:00:00 UTC", () => {
    expect(formatUtc("2026-01-01T00:00:00+00:00")).toBe("2026-01-01 00:00:00 UTC");
  });

  it("formats leap-day noon", () => {
    expect(formatUtc("2024-02-29T12:30:45+00:00")).toBe("2024-02-29 12:30:45 UTC");
  });

  it("converts offsets to UTC", () => {
    expect(formatUtc("2026-01-01T02:00:00+02:00")).toBe("2026-01-01 00:00:00 UTC");
  });
});

describe("reserve and load text", () => {
  it("formats reserve text", () => {
    expect(formatReserve(23)).toBe("Reserve Level 23 / 100");
  });

  it("formats recovery load", () => {
    expect(formatRecoveryLoad("critical")).toBe("Recovery Load: critical");
  });
});

describe("formatValidationError", () => {
  it("passes through strings", () => {
    expect(formatValidationError("bad")).toBe("bad");
  });

  it("flattens array details with loc", () => {
    const detail = [{ loc: ["body", "events", 3, "type"], msg: "unexpected value" }];
    expect(formatValidationError(detail)).toBe("body.events.3.type: unexpected value");
  });

  it("pretty-prints duplicate_event_ids object", () => {
    const detail = { message: "duplicate event_id", duplicate_event_ids: ["evt-01"] };
    const out = formatValidationError(detail);
    expect(out).toContain("duplicate event_id");
    expect(out).toContain('["evt-01"]');
  });

  it("pretty-prints unknown object shapes as JSON", () => {
    const detail = { foo: 1, bar: [1, 2] };
    expect(formatValidationError(detail)).toBe(JSON.stringify(detail, null, 2));
  });

  it("handles missing detail", () => {
    expect(formatValidationError(null)).toBe("Validation failed.");
    expect(formatValidationError(undefined)).toBe("Validation failed.");
  });
});
