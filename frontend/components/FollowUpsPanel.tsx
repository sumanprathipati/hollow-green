import type { RecoveryFollowUp } from "@/lib/types";

export default function FollowUpsPanel({ followUps }: { followUps: RecoveryFollowUp[] }) {
  return (
    <section aria-label="Recovery follow-ups" className="rounded border p-3">
      <h2 className="text-sm font-medium">Recovery Follow-ups</h2>
      {followUps.length === 0 ? (
        <p className="mt-2 text-sm">No follow-ups.</p>
      ) : (
        <ul className="mt-2 flex flex-col gap-2">
          {followUps.map((f) => (
            <li key={f.follow_up_id} className="rounded border p-2 text-sm">
              <p>
                <span className="font-medium">{f.kind}</span> · severity {f.severity} · status{" "}
                {f.status}
              </p>
              <p className="font-mono text-xs">source event IDs: {f.event_ids.join(", ")}</p>
              <p>Required action: {f.required_action}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
