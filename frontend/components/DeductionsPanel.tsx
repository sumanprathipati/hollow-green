import type { Deduction } from "@/lib/types";

export default function DeductionsPanel({ deductions }: { deductions: Deduction[] }) {
  return (
    <section aria-label="Deductions" className="rounded border p-3">
      <h2 className="text-sm font-medium">Deductions</h2>
      {deductions.length === 0 ? (
        <p className="mt-2 text-sm">No deductions.</p>
      ) : (
        <div className="mt-2 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left">
                <th className="pr-2">Rule ID</th>
                <th className="pr-2">Points</th>
                <th className="pr-2">Reason</th>
                <th>Event IDs</th>
              </tr>
            </thead>
            <tbody>
              {deductions.map((d, i) => (
                <tr key={`${d.rule_id}-${i}`} className="border-t">
                  <td className="pr-2 font-mono">{d.rule_id}</td>
                  <td className="pr-2">-{d.points}</td>
                  <td className="pr-2">{d.reason}</td>
                  <td className="font-mono">{d.event_ids.join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
