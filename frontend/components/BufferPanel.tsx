import type { BufferSnapshot } from "@/lib/types";

export default function BufferPanel({ buffers }: { buffers: BufferSnapshot }) {
  const rows: [string, string][] = [
    ["retries_used", String(buffers.retries_used)],
    ["retries_left", String(buffers.retries_left)],
    ["retry_reserve_pct", String(buffers.retry_reserve_pct)],
    ["time_remaining_original_pct", String(buffers.time_remaining_original_pct)],
    ["time_remaining_effective_pct", String(buffers.time_remaining_effective_pct)],
    ["extension_total_min", String(buffers.extension_total_min)],
    ["rollback_available", String(buffers.rollback_available)],
    ["rollback_fresh", String(buffers.rollback_fresh)],
    ["health_end", buffers.health_end],
    ["manual_count", String(buffers.manual_count)],
  ];
  return (
    <section aria-label="Buffers" className="rounded border p-3">
      <h2 className="text-sm font-medium">Buffers</h2>
      <dl className="mt-2 grid grid-cols-1 gap-1 text-sm md:grid-cols-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-2 border-t py-1">
            <dt className="font-mono">{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
