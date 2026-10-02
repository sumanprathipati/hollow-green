"use client";

import { useCallback, useEffect, useState } from "react";
import AnalyzeButton from "@/components/AnalyzeButton";
import AppShell from "@/components/AppShell";
import CopyReportButton from "@/components/CopyReportButton";
import DecisionHero from "@/components/DecisionHero";
import { EmptyState, ErrorState } from "@/components/EmptyErrorStates";
import EvidenceReviewCard from "@/components/EvidenceReviewCard";
import EvidenceTabs from "@/components/EvidenceTabs";
import FixturePicker from "@/components/FixturePicker";
import MetricCard from "@/components/MetricCard";
import PublicDecisionHero from "@/components/PublicDecisionHero";
import StatusBadge from "@/components/StatusBadge";
import TimelineEvent from "@/components/TimelineEvent";
import {
  analyzeRelease,
  getDemoRelease,
  getDemoReleases,
  getPublicAssessment,
  getPublicRepos,
} from "@/lib/api";
import {
  buildDecisionBrief,
  buildPublicDecisionBrief,
  getRecommendation,
  getRiskDrivers,
  toneForCompleteness,
  toneForRecoveryLoad,
  toneForSeverity,
  toneForTolerance,
} from "@/lib/decision";
import { formatUtc, formatValidationError } from "@/lib/format";
import type {
  DemoReleaseMeta,
  PublicDataAssessment,
  PublicRepoMeta,
  ReleaseLog,
  ReleaseReport,
} from "@/lib/types";
import { sortedEvents } from "@/lib/view-model";

type Phase =
  | "empty"
  | "loading-metas"
  | "loading-fixture"
  | "loading-analysis"
  | "ready"
  | "error"
  | "api-unavailable";

type PublicPhase = "idle" | "loading" | "ready" | "error" | "rate-limited" | "unavailable";
type DataMode = "demo" | "public";

function isNetworkError(e: unknown): boolean {
  return e instanceof TypeError;
}

function rollbackTone(available: boolean, verified: boolean, executed: boolean) {
  if (!available) return "red" as const;
  if (executed && !verified) return "amber" as const;
  return "emerald" as const;
}

function healthTone(health: string) {
  if (health === "pass") return "emerald" as const;
  if (health === "degraded") return "amber" as const;
  if (health === "fail") return "red" as const;
  return "slate" as const;
}

function retriesTone(left: number) {
  if (left === 0) return "red" as const;
  if (left === 1) return "amber" as const;
  return "emerald" as const;
}

export default function Home() {
  const [mode, setMode] = useState<DataMode>("demo");
  const [metas, setMetas] = useState<DemoReleaseMeta[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("loading-metas");
  const [log, setLog] = useState<ReleaseLog | null>(null);
  const [report, setReport] = useState<ReleaseReport | null>(null);
  const [analyzedAtUtc, setAnalyzedAtUtc] = useState<string>("");
  const [message, setMessage] = useState("");
  const [detail, setDetail] = useState<string | undefined>(undefined);

  const [publicRepos, setPublicRepos] = useState<PublicRepoMeta[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<string>("");
  const [assessment, setAssessment] = useState<PublicDataAssessment | null>(null);
  const [publicPhase, setPublicPhase] = useState<PublicPhase>("idle");
  const [publicMessage, setPublicMessage] = useState("");
  const [publicDetail, setPublicDetail] = useState<string | undefined>(undefined);

  const loadMetas = useCallback(async () => {
    setPhase("loading-metas");
    setMessage("Loading demo releases…");
    setDetail(undefined);
    try {
      const data = await getDemoReleases();
      setMetas(data);
      setPhase("empty");
      setMessage("Select a demo release and press Analyze release.");
    } catch (e) {
      setPhase("api-unavailable");
      setMessage("API unavailable. Is FastAPI running on http://127.0.0.1:8000?");
      setDetail(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- initial demo list load on mount only
    void loadMetas();
  }, [loadMetas]);

  const loadPublicRepos = useCallback(async () => {
    setPublicPhase("loading");
    setPublicMessage("Loading public repositories…");
    setPublicDetail(undefined);
    try {
      const data = await getPublicRepos();
      setPublicRepos(data);
      if (data.length > 0 && !selectedRepo) {
        setSelectedRepo(data[0].repo_full_name);
      }
      setPublicPhase(data.length === 0 ? "error" : "idle");
      setPublicMessage(
        data.length === 0 ? "No public repositories configured." : "Select a repository and refresh.",
      );
    } catch (e) {
      if (isNetworkError(e)) {
        setPublicPhase("unavailable");
      } else {
        setPublicPhase("error");
      }
      setPublicMessage("Could not load public repositories.");
      setPublicDetail(e instanceof Error ? e.message : String(e));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (mode === "public" && publicRepos.length === 0 && publicPhase === "idle") {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- lazy load on first entering public mode
      void loadPublicRepos();
    }
  }, [mode, publicRepos.length, publicPhase, loadPublicRepos]);

  async function fetchAssessment(repo: string, candidate: string, refresh: boolean) {
    setPublicPhase("loading");
    setPublicMessage(
      refresh ? "Refreshing assessment from GitHub…" : "Loading public evidence assessment…",
    );
    setPublicDetail(undefined);
    try {
      const data = await getPublicAssessment(
        repo,
        { candidate: candidate || undefined, refresh },
      );
      setAssessment(data);
      setSelectedCandidate(data.candidate.candidate_id);
      setAnalyzedAtUtc(formatUtc(new Date().toISOString()));
      setPublicPhase("ready");
    } catch (e) {
      if (isNetworkError(e)) {
        setPublicPhase("unavailable");
        setPublicMessage("API unavailable. Is FastAPI running on http://127.0.0.1:8000?");
        setPublicDetail(e instanceof Error ? e.message : String(e));
        return;
      }
      const err = e as { status?: number; detail?: unknown; message?: string };
      if (err.status === 429) {
        setPublicPhase("rate-limited");
        setPublicMessage("GitHub rate limit exceeded. Try again later or retry.");
      } else {
        setPublicPhase("error");
        setPublicMessage(err.status ? `Request failed (${err.status}).` : "Request failed.");
      }
      setPublicDetail(
        err.detail !== undefined && err.detail !== null
          ? formatValidationError(err.detail)
          : (err.message ?? String(e)),
      );
    }
  }

  async function onAnalyze() {
    if (!selectedId) return;
    setPhase("loading-fixture");
    setMessage("Loading fixture…");
    setDetail(undefined);
    try {
      const fetched = await getDemoRelease(selectedId);
      setLog(fetched);
      setPhase("loading-analysis");
      setMessage("Analyzing release…");
      const result = await analyzeRelease(fetched);
      setReport(result);
      setAnalyzedAtUtc(formatUtc(new Date().toISOString()));
      setPhase("ready");
    } catch (e) {
      if (isNetworkError(e)) {
        setPhase("api-unavailable");
        setMessage("API unavailable. Is FastAPI running on http://127.0.0.1:8000?");
        setDetail(e instanceof Error ? e.message : String(e));
        return;
      }
      const err = e as { status?: number; detail?: unknown; message?: string };
      setPhase("error");
      setMessage(err.status ? `Request failed (${err.status}).` : "Request failed.");
      setDetail(
        err.detail !== undefined && err.detail !== null
          ? formatValidationError(err.detail)
          : (err.message ?? String(e)),
      );
    }
  }

  const loading =
    phase === "loading-metas" || phase === "loading-fixture" || phase === "loading-analysis";
  const demoReady = mode === "demo" && phase === "ready" && report && log;
  const publicReady = mode === "public" && publicPhase === "ready" && assessment;
  const demoBrief =
    report && log
      ? buildDecisionBrief(report, log, analyzedAtUtc || formatUtc(new Date().toISOString()))
      : "";
  const publicBrief = assessment
    ? buildPublicDecisionBrief(assessment, analyzedAtUtc || formatUtc(new Date().toISOString()))
    : "";

  function onRefreshPublic() {
    if (!selectedRepo) return;
    void fetchAssessment(selectedRepo, selectedCandidate, true);
  }

  return (
    <AppShell>
      <section
        aria-label="Data mode"
        className="rounded-lg border border-slate-800 bg-slate-900 p-4"
      >
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Data source mode">
          <button
            type="button"
            aria-pressed={mode === "demo"}
            onClick={() => setMode("demo")}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              mode === "demo" ? "bg-slate-100 text-slate-900" : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            Demo scenarios
          </button>
          <button
            type="button"
            aria-pressed={mode === "public"}
            onClick={() => setMode("public")}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              mode === "public" ? "bg-slate-100 text-slate-900" : "text-slate-300 hover:bg-slate-800"
            }`}
          >
            Public GitHub evidence
          </button>
        </div>

        {mode === "demo" ? (
          <div className="mt-3 flex flex-col gap-3 md:flex-row md:items-end">
            <div className="flex-1">
              <FixturePicker
                metas={metas}
                selectedId={selectedId}
                disabled={loading}
                onChange={setSelectedId}
              />
            </div>
            <AnalyzeButton disabled={!selectedId || loading} loading={loading} onClick={onAnalyze} />
          </div>
        ) : (
          <div className="mt-3 flex flex-col gap-3">
            <p className="rounded border border-amber-300/40 bg-amber-400/10 p-2 text-sm font-medium text-amber-200">
              Public repository evidence only — deployment readiness cannot be determined.
            </p>
            <div className="flex flex-col gap-3 md:flex-row md:items-end">
              <div className="flex flex-1 flex-col gap-1">
                <label htmlFor="public-repo" className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                  Repository
                </label>
                <select
                  id="public-repo"
                  className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-100"
                  value={selectedRepo ?? ""}
                  disabled={publicPhase === "loading" || publicRepos.length === 0}
                  onChange={(e) => {
                    setSelectedRepo(e.target.value);
                    setSelectedCandidate("");
                    setAssessment(null);
                    setPublicPhase("idle");
                  }}
                >
                  <option value="">Select a repository</option>
                  {publicRepos.map((r) => (
                    <option key={r.repo_full_name} value={r.repo_full_name}>
                      {r.display_name}
                    </option>
                  ))}
                </select>
              </div>
              {assessment && assessment.evidence.candidates_available.length > 0 ? (
                <div className="flex flex-1 flex-col gap-1">
                  <label htmlFor="public-candidate" className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                    Release candidate
                  </label>
                  <select
                    id="public-candidate"
                    className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2.5 text-sm text-slate-100"
                    value={selectedCandidate}
                    disabled={publicPhase === "loading"}
                    onChange={(e) => {
                      setSelectedCandidate(e.target.value);
                      if (selectedRepo) void fetchAssessment(selectedRepo, e.target.value, false);
                    }}
                  >
                    {assessment.evidence.candidates_available.map((c) => (
                      <option key={c.candidate_id} value={c.candidate_id}>
                        {c.kind}: {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
              <button
                type="button"
                disabled={!selectedRepo || publicPhase === "loading"}
                onClick={onRefreshPublic}
                className="rounded-md bg-slate-100 px-5 py-2.5 text-sm font-semibold text-slate-900 disabled:opacity-50 hover:bg-white"
              >
                {publicPhase === "loading" ? "Refreshing…" : "Refresh assessment"}
              </button>
            </div>
            {assessment ? (
              <p className="text-xs text-slate-400">
                Source: {assessment.evidence.repo_url} · Retrieved {assessment.retrieved_at} ·
                Served from {assessment.served_from} · Candidate {assessment.candidate.kind}{" "}
                &apos;{assessment.candidate.name}&apos;
              </p>
            ) : null}
          </div>
        )}
      </section>

      {mode === "demo" ? (
        <>
          {phase === "empty" ? (
            <div className="mt-4">
              <EmptyState message={message} />
            </div>
          ) : null}
          {loading ? (
            <p role="status" aria-live="polite" className="mt-4 rounded-lg border border-slate-800 bg-slate-900 p-4 text-sm text-slate-200">
              {message}
            </p>
          ) : null}
          {phase === "error" ? (
            <div className="mt-4">
              <ErrorState title="Analysis failed" message={message} detail={detail} onRetry={onAnalyze} retryLabel="Retry analysis" />
            </div>
          ) : null}
          {phase === "api-unavailable" ? (
            <div className="mt-4">
              <ErrorState title="API unavailable" message={message} detail={detail} onRetry={loadMetas} retryLabel="Retry connection" />
            </div>
          ) : null}
        </>
      ) : (
        <>
          {publicPhase === "idle" ? (
            <div className="mt-4">
              <EmptyState message={publicMessage || "Select a repository and refresh."} />
            </div>
          ) : null}
          {publicPhase === "loading" ? (
            <p role="status" aria-live="polite" className="mt-4 rounded-lg border border-slate-800 bg-slate-900 p-4 text-sm text-slate-200">
              {publicMessage}
            </p>
          ) : null}
          {publicPhase === "error" ? (
            <div className="mt-4">
              <ErrorState
                title="Assessment failed"
                message={publicMessage}
                detail={publicDetail}
                onRetry={() => selectedRepo && void fetchAssessment(selectedRepo, selectedCandidate, true)}
                retryLabel="Retry assessment"
              />
            </div>
          ) : null}
          {publicPhase === "rate-limited" ? (
            <div className="mt-4">
              <ErrorState
                title="GitHub rate limit exceeded"
                message={`${publicMessage} The backend kept credentials server-side; configure GITHUB_TOKEN to raise limits. Saved data is served automatically when available.`}
                detail={publicDetail}
                onRetry={() => selectedRepo && void fetchAssessment(selectedRepo, selectedCandidate, true)}
                retryLabel="Retry assessment"
              />
            </div>
          ) : null}
          {publicPhase === "unavailable" ? (
            <div className="mt-4">
              <ErrorState
                title="API unavailable"
                message={publicMessage}
                detail={publicDetail}
                onRetry={() => void loadPublicRepos()}
                retryLabel="Retry connection"
              />
            </div>
          ) : null}
        </>
      )}

      {demoReady && report && log ? (
        <div className="mt-4 flex flex-col gap-4">
          <DecisionHero
            report={report}
            recommendation={getRecommendation(report.classification)}
            analyzedAtUtc={analyzedAtUtc}
          />

          <section aria-label="Operational metrics" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Reserve Level"
              value={`${report.score.reserve_level} / 100`}
              sub={`Recovery Load ${report.score.recovery_load}`}
              tone={toneForRecoveryLoad(report.score.recovery_load)}
              badgeLabel={report.score.recovery_load}
            />
            <MetricCard
              label="Retries left"
              value={String(report.score.buffers.retries_left)}
              sub={`${report.score.buffers.retries_used} used`}
              tone={retriesTone(report.score.buffers.retries_left)}
              badgeLabel={report.score.buffers.retries_left === 0 ? "exhausted" : "available"}
            />
            <MetricCard
              label="Rollback"
              value={report.score.buffers.rollback_available ? "Available" : "Unavailable"}
              sub={
                report.rollback_summary.executed
                  ? `executed · ${report.rollback_summary.verified ? "verified" : "unverified"}${report.rollback_summary.manual ? " · manual" : ""}`
                  : "not executed"
              }
              tone={rollbackTone(
                report.score.buffers.rollback_available,
                report.rollback_summary.verified,
                report.rollback_summary.executed,
              )}
              badgeLabel={
                !report.score.buffers.rollback_available
                  ? "unavailable"
                  : report.rollback_summary.executed && !report.rollback_summary.verified
                    ? "unverified"
                    : "ready"
              }
            />
            <MetricCard
              label="Health at end"
              value={report.score.buffers.health_end}
              sub={`${report.score.buffers.manual_count} manual interventions`}
              tone={healthTone(report.score.buffers.health_end)}
              badgeLabel={report.score.buffers.health_end}
            />
          </section>

          <section className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <h2 className="text-sm font-semibold text-slate-100">Why this result</h2>
              <p className="mt-1 text-sm text-slate-300">
                Classification {report.classification} · {report.score.deductions.length} deduction(s)
              </p>
              <ul className="mt-3 flex flex-col gap-2">
                {getRiskDrivers(report, 3).map((d) => (
                  <li key={d.rule_id} className="rounded border border-slate-800 bg-slate-950 p-2.5 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono text-xs text-slate-200">{d.rule_id}</span>
                      <StatusBadge tone="slate" label={`-${d.points}`} icon="−" />
                    </div>
                    <p className="mt-1 text-slate-200">{d.reason}</p>
                    <p className="mt-0.5 font-mono text-xs text-slate-400">
                      evidence: {d.event_ids.join(", ")}
                    </p>
                  </li>
                ))}
                {getRiskDrivers(report, 3).length === 0 ? (
                  <li className="text-sm text-slate-300">No deductions. Capacity intact.</li>
                ) : null}
              </ul>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-slate-100">Operational readiness</h2>
                <StatusBadge tone={toneForTolerance(report.tolerance.level)} label={report.tolerance.level} />
              </div>
              <p className="mt-1 text-sm text-slate-300">
                {report.tolerance.can_survive_second_failure
                  ? "Can survive a second failure."
                  : "Cannot survive a second failure."}{" "}
                {report.score.buffers.retries_left} retries left.
              </p>
              <ul className="mt-3 list-disc pl-5 text-sm text-slate-200">
                {report.tolerance.rationale.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
              <div className="mt-3">
                <CopyReportButton briefText={demoBrief} />
              </div>
            </div>
          </section>

          <section aria-label="Event timeline" className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="text-sm font-semibold text-slate-100">Release timeline</h2>
            <p className="mt-0.5 text-xs text-slate-400">Sorted by timestamp. Times shown in UTC.</p>
            <ol className="mt-3">
              {sortedEvents(log.events).map((e) => (
                <TimelineEvent key={e.event_id} event={e} />
              ))}
            </ol>
          </section>

          <EvidenceTabs
            deductions={
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-300">
                      <th className="pr-2 font-medium">Rule</th>
                      <th className="pr-2 font-medium">Points</th>
                      <th className="pr-2 font-medium">Reason</th>
                      <th className="font-medium">Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.score.deductions.map((d, i) => (
                      <tr key={`${d.rule_id}-${i}`} className="border-t border-slate-800 text-slate-100">
                        <td className="py-1.5 pr-2 font-mono text-xs">{d.rule_id}</td>
                        <td className="py-1.5 pr-2">-{d.points}</td>
                        <td className="py-1.5 pr-2">{d.reason}</td>
                        <td className="py-1.5 font-mono text-xs text-slate-300">
                          {d.event_ids.join(", ")}
                        </td>
                      </tr>
                    ))}
                    {report.score.deductions.length === 0 ? (
                      <tr>
                        <td colSpan={4} className="py-2 text-slate-300">
                          No deductions.
                        </td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            }
            buffers={
              <dl className="grid grid-cols-1 gap-1 text-sm md:grid-cols-2">
                {(
                  [
                    ["retries_used", String(report.score.buffers.retries_used)],
                    ["retries_left", String(report.score.buffers.retries_left)],
                    ["retry_reserve_pct", String(report.score.buffers.retry_reserve_pct)],
                    ["time_remaining_original_pct", String(report.score.buffers.time_remaining_original_pct)],
                    ["time_remaining_effective_pct", String(report.score.buffers.time_remaining_effective_pct)],
                    ["extension_total_min", String(report.score.buffers.extension_total_min)],
                    ["rollback_available", String(report.score.buffers.rollback_available)],
                    ["rollback_fresh", String(report.score.buffers.rollback_fresh)],
                    ["health_end", report.score.buffers.health_end],
                    ["manual_count", String(report.score.buffers.manual_count)],
                  ] as [string, string][]
                ).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-2 border-t border-slate-800 py-1.5">
                    <dt className="font-mono text-xs text-slate-300">{k}</dt>
                    <dd className="text-slate-100">{v}</dd>
                  </div>
                ))}
              </dl>
            }
            followUps={
              report.follow_ups.length === 0 ? (
                <p className="text-sm text-slate-300">No follow-ups.</p>
              ) : (
                <ul className="flex flex-col gap-2">
                  {report.follow_ups.map((f) => (
                    <li key={f.follow_up_id} className="rounded border border-slate-800 bg-slate-950 p-2.5 text-sm">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-slate-100">{f.kind}</span>
                        <StatusBadge tone={toneForSeverity(f.severity)} label={f.severity} />
                        <span className="text-xs text-slate-400">status {f.status}</span>
                      </div>
                      <p className="mt-1 text-slate-200">Required action: {f.required_action}</p>
                      <p className="mt-0.5 font-mono text-xs text-slate-400">
                        source event IDs: {f.event_ids.join(", ")}
                      </p>
                    </li>
                  ))}
                </ul>
              )
            }
            audit={
              <div className="flex flex-col gap-3">
                <p className="text-sm text-slate-300">
                  Optional audit view. Raw backend payloads for verification only.
                </p>
                <details className="rounded border border-slate-800">
                  <summary className="cursor-pointer p-2 text-sm font-medium text-slate-100">
                    View raw ReleaseReport JSON
                  </summary>
                  <pre className="max-h-96 overflow-auto border-t border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-200">
                    {JSON.stringify(report, null, 2)}
                  </pre>
                </details>
                <details className="rounded border border-slate-800">
                  <summary className="cursor-pointer p-2 text-sm font-medium text-slate-100">
                    View raw ReleaseLog event detail
                  </summary>
                  <pre className="max-h-96 overflow-auto border-t border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-200">
                    {JSON.stringify(log, null, 2)}
                  </pre>
                </details>
              </div>
            }
          />
        </div>
      ) : null}

      {publicReady && assessment ? (
        <div className="mt-4 flex flex-col gap-4">
          <PublicDecisionHero assessment={assessment} />

          <section className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-slate-100">Evidence completeness</h2>
                <StatusBadge
                  tone={toneForCompleteness(assessment.public_result.evidence_completeness)}
                  label={assessment.public_result.evidence_completeness}
                />
              </div>
              <p className="mt-1 text-sm text-slate-300">
                {assessment.evidence.commits_recent.length} commits,{" "}
                {assessment.evidence.pulls_recent.length} pull requests,{" "}
                {assessment.evidence.issues_open_sample.length} sampled open issues observed.
              </p>
              <div className="mt-3">
                <CopyReportButton briefText={publicBrief} />
              </div>
            </div>
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <h2 className="text-sm font-semibold text-slate-100">Unavailable operational signals</h2>
              <p className="mt-1 text-sm text-slate-300">
                These cannot be observed from public data and do not affect the change-risk
                level. Deployment readiness: {assessment.public_result.deployment_readiness}.
              </p>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {assessment.unavailable_signals.map((s) => (
                  <li key={s}>
                    <StatusBadge tone="slate" label={s} icon="●" />
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <EvidenceReviewCard
            key={`${assessment.repo_full_name}|${assessment.candidate.candidate_id}`}
            owner={assessment.repo_full_name.split("/")[0]}
            repo={assessment.repo_full_name.split("/")[1]}
            candidate={assessment.candidate.candidate_id}
            recommendation={assessment.public_result.public_recommendation}
          />

          <section aria-label="Source evidence" className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="text-sm font-semibold text-slate-100">Source evidence (public GitHub)</h2>
            <p className="mt-1 text-sm text-slate-300">
              Repository{" "}
              <a href={assessment.evidence.repo_url} target="_blank" rel="noreferrer" className="underline">
                {assessment.repo_full_name}
              </a>{" "}
              · {assessment.evidence.stars} stars · {assessment.evidence.open_issues_count} open
              issues · branch {assessment.evidence.default_branch}
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Retrieved {assessment.retrieved_at} · Served from {assessment.served_from} ·
              Candidate {assessment.candidate.kind} &apos;{assessment.candidate.name}&apos; (
              <a href={assessment.candidate.url} target="_blank" rel="noreferrer" className="underline">
                source
              </a>
              )
            </p>
            <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-3">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Recent commits</h3>
                <ul className="mt-1 flex flex-col gap-1 text-sm">
                  {assessment.evidence.commits_recent.map((c) => (
                    <li key={c.sha}>
                      <a href={c.url} target="_blank" rel="noreferrer" className="underline">
                        {c.sha.slice(0, 7)}
                      </a>{" "}
                      <span className="text-slate-300">{c.message}</span>
                    </li>
                  ))}
                  {assessment.evidence.commits_recent.length === 0 ? (
                    <li className="text-slate-400">None observed.</li>
                  ) : null}
                </ul>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Pull requests</h3>
                <ul className="mt-1 flex flex-col gap-1 text-sm">
                  {assessment.evidence.pulls_recent.map((p) => (
                    <li key={p.number}>
                      <a href={p.url} target="_blank" rel="noreferrer" className="underline">
                        #{p.number}
                      </a>{" "}
                      <span className="text-slate-300">{p.title} ({p.state})</span>
                    </li>
                  ))}
                  {assessment.evidence.pulls_recent.length === 0 ? (
                    <li className="text-slate-400">None observed.</li>
                  ) : null}
                </ul>
              </div>
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-400">Open issues</h3>
                <ul className="mt-1 flex flex-col gap-1 text-sm">
                  {assessment.evidence.issues_open_sample.map((issue) => (
                    <li key={issue.number}>
                      <a href={issue.url} target="_blank" rel="noreferrer" className="underline">
                        #{issue.number}
                      </a>{" "}
                      <span className="text-slate-300">{issue.title}</span>
                    </li>
                  ))}
                  {assessment.evidence.issues_open_sample.length === 0 ? (
                    <li className="text-slate-400">None observed.</li>
                  ) : null}
                </ul>
              </div>
            </div>
            <h3 className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Limitations</h3>
            <ul className="mt-1 list-disc pl-5 text-sm text-slate-200">
              {assessment.limitations.map((lim, i) => (
                <li key={i}>{lim}</li>
              ))}
            </ul>
          </section>

          <section aria-label="Public activity timeline" className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <h2 className="text-sm font-semibold text-slate-100">Observed activity</h2>
            <p className="mt-0.5 text-xs text-slate-400">Public commits and candidate publication. Times in UTC.</p>
            <ol className="mt-3">
              {assessment.evidence.commits_recent.map((c) => (
                <li key={c.sha} className="relative border-l border-slate-700 pl-4 pb-4 last:pb-0">
                  <span aria-hidden="true" className="absolute -left-1.5 top-1 h-3 w-3 rounded-full border border-slate-500 bg-slate-900" />
                  <p className="font-mono text-xs text-slate-300">{c.date ?? "date unknown"} · {c.sha.slice(0, 7)}</p>
                  <p className="mt-0.5 text-sm font-medium text-slate-100">
                    commit <span className="font-normal text-slate-300">· {c.message}</span>
                  </p>
                  <p className="text-xs text-slate-400">
                    <a href={c.url} target="_blank" rel="noreferrer" className="underline">source</a>
                  </p>
                </li>
              ))}
              <li className="relative border-l border-slate-700 pl-4 pb-0">
                <span aria-hidden="true" className="absolute -left-1.5 top-1 h-3 w-3 rounded-full border border-slate-500 bg-slate-900" />
                <p className="font-mono text-xs text-slate-300">{assessment.candidate.published_at ?? "date unknown"}</p>
                <p className="mt-0.5 text-sm font-medium text-slate-100">
                  {assessment.candidate.kind} &apos;{assessment.candidate.name}&apos;
                </p>
                <p className="text-xs text-slate-400">
                  <a href={assessment.candidate.url} target="_blank" rel="noreferrer" className="underline">source</a>
                </p>
              </li>
            </ol>
          </section>

          <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
            <details className="rounded border border-slate-800">
              <summary className="cursor-pointer p-2 text-sm font-medium text-slate-100">
                View raw public evidence JSON (audit only)
              </summary>
              <pre className="max-h-96 overflow-auto border-t border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-200">
                {JSON.stringify(assessment, null, 2)}
              </pre>
            </details>
          </div>
        </div>
      ) : null}
    </AppShell>
  );
}
