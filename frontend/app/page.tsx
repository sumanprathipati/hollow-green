"use client";

import { useCallback, useEffect, useState } from "react";
import AnalyzeButton from "@/components/AnalyzeButton";
import BufferPanel from "@/components/BufferPanel";
import CopyReportButton from "@/components/CopyReportButton";
import DeductionsPanel from "@/components/DeductionsPanel";
import EventTimeline from "@/components/EventTimeline";
import FixturePicker from "@/components/FixturePicker";
import FollowUpsPanel from "@/components/FollowUpsPanel";
import ReserveMeter from "@/components/ReserveMeter";
import ScoreCards from "@/components/ScoreCards";
import StatusBanner from "@/components/StatusBanner";
import { analyzeRelease, getDemoRelease, getDemoReleases } from "@/lib/api";
import { formatValidationError } from "@/lib/format";
import type { DemoReleaseMeta, ReleaseLog, ReleaseReport } from "@/lib/types";

type Phase =
  | "empty"
  | "loading-metas"
  | "loading-fixture"
  | "loading-analysis"
  | "ready"
  | "error"
  | "api-unavailable";

function isNetworkError(e: unknown): boolean {
  return e instanceof TypeError;
}

export default function Home() {
  const [metas, setMetas] = useState<DemoReleaseMeta[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase>("loading-metas");
  const [log, setLog] = useState<ReleaseLog | null>(null);
  const [report, setReport] = useState<ReleaseReport | null>(null);
  const [message, setMessage] = useState("");
  const [detail, setDetail] = useState<string | undefined>(undefined);

  const loadMetas = useCallback(async () => {
    setPhase("loading-metas");
    setMessage("Loading demo releases…");
    setDetail(undefined);
    try {
      const data = await getDemoReleases();
      setMetas(data);
      setPhase(data.length === 0 ? "empty" : "empty");
      setMessage("Select a demo release and press Analyze.");
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

  async function onAnalyze() {
    if (!selectedId) return;
    setPhase("loading-fixture");
    setMessage("Loading fixture…");
    setDetail(undefined);
    try {
      const fetched = await getDemoRelease(selectedId);
      setLog(fetched);
      setPhase("loading-analysis");
      setMessage("Analyzing…");
      const result = await analyzeRelease(fetched);
      setReport(result);
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

  const loading = phase === "loading-fixture" || phase === "loading-analysis" || phase === "loading-metas";

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-4 p-4 md:p-6">
      <header>
        <h1 className="text-2xl font-semibold">Hollow Green Dashboard</h1>
        <p className="text-sm">
          Green on the dashboard, hollow underneath. Scores are computed in Python; this page
          only displays backend results.
        </p>
      </header>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
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

      {phase === "empty" ? <StatusBanner kind="empty" message={message} /> : null}
      {loading ? <StatusBanner kind="loading" message={message} /> : null}
      {phase === "error" ? (
        <StatusBanner kind="error" message={message} detail={detail} onRetry={onAnalyze} />
      ) : null}
      {phase === "api-unavailable" ? (
        <StatusBanner kind="api-unavailable" message={message} detail={detail} onRetry={loadMetas} />
      ) : null}

      {phase === "ready" && report && log ? (
        <main className="flex flex-col gap-4">
          <ScoreCards report={report} />
          <CopyReportButton report={report} />
          <ReserveMeter
            reserve={report.score.reserve_level}
            load={report.score.recovery_load}
          />
          <DeductionsPanel deductions={report.score.deductions} />
          <BufferPanel buffers={report.score.buffers} />
          <FollowUpsPanel followUps={report.follow_ups} />
          <EventTimeline events={log.events} />
        </main>
      ) : null}
    </div>
  );
}
