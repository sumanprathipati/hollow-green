import StatusBadge from "@/components/StatusBadge";
import { toneForDecision } from "@/lib/decision";
import type { Recommendation } from "@/lib/decision";
import type { ReleaseReport } from "@/lib/types";

export default function DecisionHero({
  report,
  recommendation,
  analyzedAtUtc,
}: {
  report: ReleaseReport;
  recommendation: Recommendation;
  analyzedAtUtc: string;
}) {
  const tone = toneForDecision(recommendation.tone);
  return (
    <section
      aria-label="Release decision"
      className="rounded-lg border border-slate-800 bg-slate-900 p-5 md:p-6"
    >
      <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">
        Should this release proceed?
      </p>
      <div className="mt-2 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <h2 className="text-3xl font-bold tracking-tight text-slate-50">
          {recommendation.decision}
        </h2>
        <StatusBadge tone={tone} label={recommendation.decision} />
      </div>
      <p className="mt-2 max-w-3xl text-sm text-slate-200">{recommendation.headline}</p>
      <p className="mt-1 max-w-3xl text-sm text-slate-300">{recommendation.guidance}</p>
      <div className="mt-4 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">Confidence score</p>
          <p className="mt-1 text-4xl font-bold text-slate-50">
            {report.score.reserve_level}
            <span className="text-base font-medium text-slate-300"> / 100</span>
          </p>
          <p className="mt-1 text-sm text-slate-300">
            Risk: {report.score.recovery_load} · Release {report.release_id}
          </p>
        </div>
        <div
          role="progressbar"
          aria-valuenow={report.score.reserve_level}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Reserve Level"
          className="h-2.5 w-full overflow-hidden rounded bg-slate-800 md:max-w-xs"
        >
          <div
            className="h-full rounded bg-slate-100"
            style={{ width: `${report.score.reserve_level}%` }}
          />
        </div>
      </div>
      <p className="mt-3 text-xs text-slate-400">
        Release {report.release_id} · {report.classification} · Analyzed {analyzedAtUtc}
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Reserve Level {report.score.reserve_level} / 100 — {report.score.recovery_load} (text
        equivalent of meter)
      </p>
    </section>
  );
}
