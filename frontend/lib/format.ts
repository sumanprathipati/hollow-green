function pad(n: number): string {
  return String(n).padStart(2, "0");
}

/** Format an ISO timestamp as fixed UTC string, e.g. "2026-01-01 00:20:00 UTC". */
export function formatUtc(iso: string): string {
  const d = new Date(iso);
  const y = d.getUTCFullYear();
  const m = pad(d.getUTCMonth() + 1);
  const day = pad(d.getUTCDate());
  const h = pad(d.getUTCHours());
  const min = pad(d.getUTCMinutes());
  const s = pad(d.getUTCSeconds());
  return `${y}-${m}-${day} ${h}:${min}:${s} UTC`;
}

export function formatReserve(reserve: number): string {
  return `Reserve Level ${reserve} / 100`;
}

export function formatRecoveryLoad(load: string): string {
  return `Recovery Load: ${load}`;
}

interface ValidationItem {
  loc?: unknown;
  msg?: unknown;
}

function formatLoc(loc: unknown): string {
  if (Array.isArray(loc)) return loc.map(String).join(".");
  if (typeof loc === "string") return loc;
  return "";
}

/**
 * Flatten FastAPI 422 detail into readable lines.
 * Unknown shapes (objects, duplicate_event_ids, etc.) pretty-print as JSON.
 */
export function formatValidationError(detail: unknown): string {
  if (detail === null || detail === undefined) return "Validation failed.";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const lines = detail.map((item) => {
      if (typeof item === "string") return item;
      if (typeof item === "object" && item !== null) {
        const entry = item as ValidationItem;
        const loc = formatLoc(entry.loc);
        const msg = typeof entry.msg === "string" ? entry.msg : JSON.stringify(entry);
        return loc ? `${loc}: ${msg}` : msg;
      }
      return JSON.stringify(item);
    });
    return lines.join("\n");
  }
  if (typeof detail === "object") {
    const obj = detail as Record<string, unknown>;
    // Common backend shapes: {detail: [...]}, {message, duplicate_event_ids}
    if (typeof obj.message === "string" && obj.duplicate_event_ids !== undefined) {
      const ids = JSON.stringify(obj.duplicate_event_ids);
      return `${obj.message}\nduplicate_event_ids: ${ids}`;
    }
    return JSON.stringify(detail, null, 2);
  }
  return JSON.stringify(detail);
}
