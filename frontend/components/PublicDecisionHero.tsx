import StatusBadge from "@/components/StatusBadge";
import { toneForChangeRisk, toneForCompleteness } from "@/lib/decision";
import type { PublicDataAssessment } from "@/lib/types";

export default function PublicDecisionHero({ assessment }: { assessment: PublicDataAssessment }) {
  const r = assessment.public_result;
  return (
    <section
      aria-label="Public evidence assessment"
      className="rounded-lg border border-slate-800 bg-slate-900 p-5 md:p-6"
    >
      <p className="rounded border border-amber-300/40 bg-amber-400/10 p-2 text-sm font-semibold text-amber-200">
        Public repository evidence only — deployment readiness cannot be determined.
      </p>
      <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <h2 className="text-2xl font-bold tracking-tight text-slate-50 md:text-3xl">
          {r.public_recommendation}
        </h2>
        <div className="flex flex-wrap gap-2">
          <StatusBadge tone={toneForChangeRisk(r.change_risk_level)} label={`risk: ${r.change_risk_level}`} />
          <StatusBadge tone={toneForCompleteness(r.evidence_completeness)} label={`evidence: ${r.evidence_completeness}`} />
        </div>
      </div>
      <p className="mt-2 text-sm text-slate-300">
        Change risk {r.change_risk_level} · Evidence {r.evidence_completeness} · Deployment
        readiness: {r.deployment_readiness}
      </p>
      <ul className="mt-3 list-disc pl-5 text-sm text-slate-200">
        {r.reasons.map((reason, i) => (
          <li key={i}>{reason}</li>
        ))}
      </ul>
      <p className="mt-3 text-xs text-slate-400">
        Repository {assessment.repo_full_name} · Candidate {assessment.candidate.kind}{" "}
        &apos;{assessment.candidate.name}&apos; · Retrieved {assessment.retrieved_at} · Served
        from {assessment.served_from}
      </p>
    </section>
  );
}
