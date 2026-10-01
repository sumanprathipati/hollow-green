import type { ReleaseReport } from "@/lib/types";

export default function ScoreCards({ report }: { report: ReleaseReport }) {
  const cards = [
    { label: "Classification", value: report.classification },
    { label: "Reserve Level", value: String(report.score.reserve_level) },
    { label: "Recovery Load", value: report.score.recovery_load },
    { label: "Retries left", value: String(report.score.buffers.retries_left) },
    {
      label: "Second-failure tolerance",
      value: `${report.tolerance.level} (${report.tolerance.can_survive_second_failure ? "can survive" : "cannot survive"})`,
    },
  ];
  return (
    <section aria-label="Score summary" className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
      {cards.map((c) => (
        <div key={c.label} className="rounded border p-3">
          <h3 className="text-xs font-medium uppercase tracking-wide">{c.label}</h3>
          <p className="mt-1 text-lg font-semibold">{c.value}</p>
        </div>
      ))}
      <div className="rounded border p-3 md:col-span-2 lg:col-span-3">
        <h3 className="text-xs font-medium uppercase tracking-wide">Tolerance rationale</h3>
        <ul className="mt-1 list-disc pl-5 text-sm">
          {report.tolerance.rationale.map((r, i) => (
            <li key={i}>{r}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
