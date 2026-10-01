import { formatUtc } from "@/lib/format";
import type { DeploymentEvent } from "@/lib/types";

export default function TimelineEvent({ event }: { event: DeploymentEvent }) {
  return (
    <li className="relative border-l border-slate-700 pl-4 pb-4 last:pb-0">
      <span
        aria-hidden="true"
        className="absolute -left-1.5 top-1 h-3 w-3 rounded-full border border-slate-500 bg-slate-900"
      />
      <p className="font-mono text-xs text-slate-300">
        {formatUtc(event.ts)} · {event.event_id}
      </p>
      <p className="mt-0.5 text-sm font-medium text-slate-100">
        {event.type} <span className="font-normal text-slate-300">· {event.actor}</span>
      </p>
      {event.severity ? <p className="text-xs text-slate-400">severity: {event.severity}</p> : null}
    </li>
  );
}
