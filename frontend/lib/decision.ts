import type {
  Classification,
  PublicDataAssessment,
  ReleaseLog,
  ReleaseReport,
} from "@/lib/types";

export type DecisionTone = "proceed" | "caution" | "rollback" | "hold";

export interface Recommendation {
  decision: "PROCEED" | "PROCEED WITH CAUTION" | "ROLLBACK VERIFIED" | "HOLD / INVESTIGATE";
  tone: DecisionTone;
  headline: string;
  guidance: string;
}

export function getRecommendation(classification: Classification): Recommendation {
  switch (classification) {
    case "clean_success":
      return {
        decision: "PROCEED",
        tone: "proceed",
        headline: "Release looks clean. Recovery capacity is intact.",
        guidance: "Proceed with normal release controls.",
      };
    case "recovered_success":
      return {
        decision: "PROCEED WITH CAUTION",
        tone: "caution",
        headline: "Release succeeded but consumed recovery capacity.",
        guidance: "Proceed with caution. Review risk drivers and restore consumed buffers.",
      };
    case "fragile_success":
      return {
        decision: "PROCEED WITH CAUTION",
        tone: "caution",
        headline: "Release succeeded but is fragile. Capacity is thin.",
        guidance: "Proceed with caution. Address required follow-ups before the next release.",
      };
    case "rollback":
      return {
        decision: "ROLLBACK VERIFIED",
        tone: "rollback",
        headline: "Release was rolled back. Verify safety before retry.",
        guidance: "Confirm rollback verification and health before re-attempting the release.",
      };
    case "failed":
      return {
        decision: "HOLD / INVESTIGATE",
        tone: "hold",
        headline: "Release failed. Do not proceed.",
        guidance: "Hold. Investigate failure causes and complete required follow-ups.",
      };
  }
}

export type BadgeTone = "emerald" | "amber" | "red" | "slate" | "sky";

export function toneForDecision(tone: DecisionTone): BadgeTone {
  if (tone === "proceed") return "emerald";
  if (tone === "caution") return "amber";
  if (tone === "rollback") return "sky";
  return "red";
}

export function toneForRecoveryLoad(load: string): BadgeTone {
  if (load === "low") return "emerald";
  if (load === "medium") return "amber";
  if (load === "high") return "amber";
  return "red";
}

export function toneForTolerance(level: string): BadgeTone {
  if (level === "high") return "emerald";
  if (level === "medium") return "amber";
  return "red";
}

export function toneForSeverity(severity: string): BadgeTone {
  if (severity === "low") return "emerald";
  if (severity === "medium") return "amber";
  if (severity === "high") return "amber";
  if (severity === "critical") return "red";
  return "slate";
}

export function toneForChangeRisk(level: string): BadgeTone {
  if (level === "low") return "emerald";
  if (level === "moderate") return "amber";
  if (level === "elevated") return "red";
  return "slate";
}

export function toneForCompleteness(level: string): BadgeTone {
  if (level === "sufficient") return "emerald";
  if (level === "limited") return "amber";
  return "slate";
}

export interface RiskDriver {
  rule_id: string;
  points: number;
  reason: string;
  event_ids: string[];
}

/** Display-only ordering of deductions by points desc. Scoring stays in Python. */
export function getRiskDrivers(report: ReleaseReport, limit = 3): RiskDriver[] {
  return [...report.score.deductions]
    .sort((a, b) => b.points - a.points)
    .slice(0, limit)
    .map((d) => ({
      rule_id: d.rule_id,
      points: d.points,
      reason: d.reason,
      event_ids: d.event_ids,
    }));
}

export function buildDecisionBrief(
  report: ReleaseReport,
  log: ReleaseLog,
  analyzedAtUtc: string,
): string {
  const rec = getRecommendation(report.classification);
  const drivers = getRiskDrivers(report, 5);
  const lines: string[] = [];
  lines.push("Hollow Green — Release Decision Brief");
  lines.push("Synthetic demo environment. Scores computed by the Python backend.");
  lines.push("");
  lines.push(`Release: ${report.release_id} (${report.classification})`);
  lines.push(`Decision: ${rec.decision}`);
  lines.push(`Guidance: ${rec.guidance}`);
  lines.push(`Reserve Level: ${report.score.reserve_level} / 100 (${report.score.recovery_load})`);
  lines.push(
    `Tolerance: ${report.tolerance.level} — ${report.tolerance.can_survive_second_failure ? "can survive a second failure" : "cannot survive a second failure"}`,
  );
  lines.push(`Retries left: ${report.score.buffers.retries_left}`);
  lines.push(`Rollback: executed=${String(report.rollback_summary.executed)} verified=${String(report.rollback_summary.verified)} manual=${String(report.rollback_summary.manual)}`);
  lines.push(`Health at end: ${report.score.buffers.health_end}`);
  lines.push(`Analyzed: ${analyzedAtUtc}`);
  lines.push(`Service: ${log.service} · Window: ${log.window_minutes}m · Retry budget: ${log.retry_budget_max}`);
  lines.push("");
  lines.push("Key risk drivers:");
  if (drivers.length === 0) {
    lines.push("- None. No deductions.");
  } else {
    for (const d of drivers) {
      lines.push(`- ${d.rule_id} (-${d.points}): ${d.reason} [${d.event_ids.join(", ")}]`);
    }
  }
  lines.push("");
  lines.push("Operational readiness:");
  for (const r of report.tolerance.rationale) {
    lines.push(`- ${r}`);
  }
  lines.push("");
  lines.push("Required follow-ups:");
  if (report.follow_ups.length === 0) {
    lines.push("- None open.");
  } else {
    for (const f of report.follow_ups) {
      lines.push(
        `- [${f.severity}] ${f.kind} (${f.follow_up_id}): ${f.required_action} [${f.event_ids.join(", ")}] status=${f.status}`,
      );
    }
  }
  lines.push("");
  lines.push("Evidence IDs:");
  lines.push(`- Deductions: ${report.score.deductions.map((d) => d.rule_id).join(", ") || "none"}`);
  lines.push(`- Events: ${log.events.map((e) => e.event_id).join(", ")}`);
  return lines.join("\n");
}

export function buildPublicDecisionBrief(
  assessment: PublicDataAssessment,
  analyzedAtUtc: string,
): string {
  const r = assessment.public_result;
  const lines: string[] = [];
  lines.push("Hollow Green — Public Evidence Brief");
  lines.push("Public repository evidence only — deployment readiness cannot be determined.");
  lines.push(`Scores are not computed for public evidence; served_from=${assessment.served_from}.`);
  lines.push("");
  lines.push(`Repository: ${assessment.repo_full_name} (${assessment.evidence.repo_url})`);
  lines.push(`Candidate: ${assessment.candidate.kind} '${assessment.candidate.name}' (${assessment.candidate.url})`);
  lines.push(`Change risk: ${r.change_risk_level} · Evidence: ${r.evidence_completeness}`);
  lines.push(`Deployment readiness: ${r.deployment_readiness}`);
  lines.push(`Recommendation: ${r.public_recommendation}`);
  lines.push(`Retrieved: ${assessment.retrieved_at} · Briefed: ${analyzedAtUtc}`);
  lines.push(`Sources: ${assessment.source_urls.join(", ") || "none"}`);
  lines.push("");
  lines.push("Observed change signals:");
  for (const reason of r.reasons) {
    lines.push(`- ${reason}`);
  }
  lines.push("");
  lines.push("Recent commits:");
  if (assessment.evidence.commits_recent.length === 0) {
    lines.push("- None observed.");
  } else {
    for (const c of assessment.evidence.commits_recent) {
      lines.push(`- ${c.sha.slice(0, 7)}: ${c.message} (${c.url})`);
    }
  }
  lines.push("");
  lines.push("Limitations:");
  for (const lim of assessment.limitations) {
    lines.push(`- ${lim}`);
  }
  lines.push(`Unavailable signals: ${assessment.unavailable_signals.join(", ")}`);
  return lines.join("\n");
}
