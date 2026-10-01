import StatusBadge from "@/components/StatusBadge";
import type { BadgeTone } from "@/lib/decision";

export default function MetricCard({
  label,
  value,
  sub,
  tone,
  badgeLabel,
}: {
  label: string;
  value: string;
  sub: string;
  tone: BadgeTone;
  badgeLabel: string;
}) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">{label}</h3>
        <StatusBadge tone={tone} label={badgeLabel} />
      </div>
      <p className="mt-2 text-2xl font-bold text-slate-50">{value}</p>
      <p className="mt-1 text-sm text-slate-300">{sub}</p>
    </div>
  );
}
