import type { ReactNode } from "react";
import { useRef, useState } from "react";

const tabs = ["Deductions", "Buffers", "Follow-ups", "Audit"] as const;
export type EvidenceTab = (typeof tabs)[number];

function tabId(tab: EvidenceTab): string {
  return `evidence-tab-${tab.toLowerCase()}`;
}

function panelId(tab: EvidenceTab): string {
  return `evidence-panel-${tab.toLowerCase()}`;
}

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
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  function focusTab(index: number): void {
    const count = tabs.length;
    const next = ((index % count) + count) % count;
    setActive(tabs[next]);
    tabRefs.current[next]?.focus();
  }

  function onKeyDown(event: React.KeyboardEvent, index: number): void {
    if (event.key === "ArrowRight") {
      event.preventDefault();
      focusTab(index + 1);
    } else if (event.key === "ArrowLeft") {
      event.preventDefault();
      focusTab(index - 1);
    } else if (event.key === "Home") {
      event.preventDefault();
      focusTab(0);
    } else if (event.key === "End") {
      event.preventDefault();
      focusTab(tabs.length - 1);
    }
  }

  return (
    <section aria-label="Evidence" className="rounded-lg border border-slate-800 bg-slate-900">
      <div role="tablist" aria-label="Evidence views" className="flex flex-wrap gap-1 border-b border-slate-800 p-2">
        {tabs.map((t, index) => (
          <button
            key={t}
            ref={(el) => {
              tabRefs.current[index] = el;
            }}
            role="tab"
            id={tabId(t)}
            aria-selected={active === t}
            aria-controls={panelId(t)}
            tabIndex={active === t ? 0 : -1}
            type="button"
            onClick={() => setActive(t)}
            onKeyDown={(event) => onKeyDown(event, index)}
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
      <div
        role="tabpanel"
        id={panelId(active)}
        aria-labelledby={tabId(active)}
        tabIndex={0}
        className="p-4"
      >
        {active === "Deductions" ? deductions : null}
        {active === "Buffers" ? buffers : null}
        {active === "Follow-ups" ? followUps : null}
        {active === "Audit" ? audit : null}
      </div>
    </section>
  );
}
