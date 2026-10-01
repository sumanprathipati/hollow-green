import type {
  Deduction,
  DeploymentEvent,
  RecoveryFollowUp,
  ReleaseLog,
  ReleaseReport,
} from "@/lib/types";

export interface CardRow {
  label: string;
  value: string;
}

export function scoreCards(report: ReleaseReport): CardRow[] {
  return [
    { label: "Classification", value: report.classification },
    { label: "Reserve Level", value: String(report.score.reserve_level) },
    { label: "Recovery Load", value: report.score.recovery_load },
    { label: "Retries left", value: String(report.score.buffers.retries_left) },
    { label: "Second-failure tolerance", value: report.tolerance.level },
  ];
}

export function sortedEvents(events: DeploymentEvent[]): DeploymentEvent[] {
  return [...events].sort((a, b) => {
    if (a.ts < b.ts) return -1;
    if (a.ts > b.ts) return 1;
    if (a.event_id < b.event_id) return -1;
    if (a.event_id > b.event_id) return 1;
    return 0;
  });
}

export function deductionRows(report: ReleaseReport): Deduction[] {
  return report.score.deductions;
}

export function followUpRows(report: ReleaseReport): RecoveryFollowUp[] {
  return report.follow_ups;
}

/** Map an engine event ID to its public source URL, if the mapper recorded one. */
export function evidenceUrlForEvent(log: ReleaseLog, eventId: string): string | null {
  const event = log.events.find((e) => e.event_id === eventId);
  const url = event?.details?.source_url;
  return typeof url === "string" && url.length > 0 ? url : null;
}
