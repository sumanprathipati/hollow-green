import { formatUtc } from "@/lib/format";
import type { DeploymentEvent } from "@/lib/types";
import { sortedEvents } from "@/lib/view-model";

export default function EventTimeline({ events }: { events: DeploymentEvent[] }) {
  const ordered = sortedEvents(events);
  return (
    <section aria-label="Event timeline" className="rounded border p-3">
      <h2 className="text-sm font-medium">Event timeline</h2>
      <ol className="mt-2 flex flex-col gap-1 text-sm">
        {ordered.map((e) => (
          <li key={e.event_id} className="border-t py-1">
            <p className="font-mono text-xs">
              {formatUtc(e.ts)} · {e.event_id}
            </p>
            <p>
              {e.type} · {e.actor}
              {e.severity ? ` · ${e.severity}` : ""}
            </p>
          </li>
        ))}
      </ol>
    </section>
  );
}
