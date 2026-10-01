import type { BadgeTone } from "@/lib/decision";

const styles: Record<BadgeTone, string> = {
  emerald: "border-emerald-300/40 bg-emerald-400/10 text-emerald-200",
  amber: "border-amber-300/40 bg-amber-400/10 text-amber-200",
  red: "border-red-300/40 bg-red-400/10 text-red-200",
  slate: "border-slate-600 bg-slate-800 text-slate-200",
  sky: "border-sky-300/40 bg-sky-400/10 text-sky-200",
};

const icons: Record<BadgeTone, string> = {
  emerald: "✓",
  amber: "!",
  red: "■",
  slate: "●",
  sky: "↩",
};

export default function StatusBadge({
  tone,
  label,
  icon,
}: {
  tone: BadgeTone;
  label: string;
  icon?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${styles[tone]}`}
    >
      <span aria-hidden="true">{icon ?? icons[tone]}</span>
      {label}
    </span>
  );
}
