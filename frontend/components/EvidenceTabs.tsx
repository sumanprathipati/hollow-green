import type { ReactNode } from "react";
import { useState } from "react";

const tabs = ["Deductions", "Buffers", "Follow-ups", "Audit"] as const;
export type EvidenceTab = (typeof tabs)[number];

export default function EvidenceTabs({
  deductions,
  buffers,
  followUps,
  audit,
}: {
  deductions: ReactNode;
  buffers: ReactNode;
  followUps: ReactNode;
  audit: ReactNode;
}) {
  const [active, setActive] = useState<EvidenceTab>("Deductions");
  return (
    <section aria-label="Evidence" className="rounded-lg border border-slate-800 bg-slate-900">
      <div role="tablist" aria-label="Evidence views" className="flex flex-wrap gap-1 border-b border-slate-800 p-2">
        {tabs.map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={active === t}
            type="button"
            onClick={() => setActive(t)}
            className={`rounded px-3 py-1.5 text-sm font-medium ${
              active === t
                ? "bg-slate-100 text-slate-900"
                : "text-slate-300 hover:bg-slate-800 hover:text-slate-100"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <div role="tabpanel" className="p-4">
        {active === "Deductions" ? deductions : null}
        {active === "Buffers" ? buffers : null}
        {active === "Follow-ups" ? followUps : null}
        {active === "Audit" ? audit : null}
      </div>
    </section>
  );
}
