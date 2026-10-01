"use client";

import { useState } from "react";
import { requestEvidenceReview } from "@/lib/api";
import {
  REVIEW_SECTION_ORDER,
  canRegenerate,
  reviewSectionTitle,
  reviewStatusCopy,
  type ReviewSectionKey,
} from "@/lib/evidence-review";
import type {
  EvidenceReviewResponse,
  EvidenceReviewSource,
} from "@/lib/types";

type CardState =
  | "idle"
  | "loading"
  | "unavailable"
  | "error"
  | "rate-limited"
  | "blocked"
  | "available";

function sourceById(
  sources: EvidenceReviewSource[],
  id: string,
): EvidenceReviewSource | null {
  return sources.find((s) => s.id === id) ?? null;
}

function CitedText({ text, sources }: { text: string; sources: EvidenceReviewSource[] }) {
  const parts = text.split(/(\[E[1-9][0-9]*\])/g);
  return (
    <span>
      {parts.map((part, i) => {
        const match = /^\[(E[1-9][0-9]*)\]$/.exec(part);
        if (!match) return <span key={i}>{part}</span>;
        const source = sourceById(sources, match[1]);
        if (!source) return <span key={i}>{part}</span>;
        return (
          <a
            key={i}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            aria-label={`Source ${source.id}: ${source.label} (external link)`}
            className="ml-1 inline-flex items-center gap-0.5 rounded border border-slate-600 px-1.5 py-px font-mono text-xs text-sky-300 underline"
          >
            {source.id}
          </a>
        );
      })}
    </span>
  );
}

export default function EvidenceReviewCard({
  owner,
  repo,
  candidate,
  recommendation,
}: {
  owner: string;
  repo: string;
  candidate: string;
  recommendation: string;
}) {
  const [state, setState] = useState<CardState>("idle");
  const [review, setReview] = useState<EvidenceReviewResponse | null>(null);
  const [detail, setDetail] = useState<string | undefined>(undefined);

  async function generate(regenerate: boolean) {
    setState("loading");
    setDetail(undefined);
    try {
      const body = await requestEvidenceReview(owner, repo, candidate, { regenerate });
      if (body.status === "available" && body.sections) {
        setReview(body);
        setState("available");
      } else if (body.status === "unavailable") {
        setReview(body);
        setState("unavailable");
      } else if (body.status === "blocked") {
        setReview(body);
        setState("blocked");
      } else {
        setReview(body);
        setState("error");
        setDetail(body.message ?? undefined);
      }
    } catch (e) {
      const err = e as { status?: number; detail?: unknown; message?: string };
      if (err.status === 429) {
        setState("rate-limited");
        setDetail(
          typeof err.detail === "string" ? err.detail : (err.message ?? String(e)),
        );
      } else {
        setState("error");
        setDetail(err.message ?? String(e));
      }
    }
  }

  function sectionTitle(key: ReviewSectionKey): string {
    return reviewSectionTitle(key, recommendation);
  }

  return (
    <section
      aria-label="AI-assisted evidence review"
      className="rounded-lg border border-slate-800 bg-slate-900 p-4"
    >
      <h2 className="text-sm font-semibold text-slate-100">AI-assisted evidence review</h2>
      <p className="mt-1 text-sm text-slate-300">
        Generated only from the repository evidence shown below. Review source citations
        before acting.
      </p>
      <p className="mt-1 text-xs text-slate-400">
        Only normalized evidence for the selected public repository is sent to the
        configured AI provider.
      </p>
      <p className="mt-1 text-xs font-medium text-amber-200">
        Public repository evidence only — deployment readiness cannot be determined.
      </p>

      {state === "idle" ? (
        <div className="mt-3">
          <p className="text-sm text-slate-300">
            Get a short, cited explanation of this deterministic assessment, its evidence
            gaps, and suggested human checks.
          </p>
          <button
            type="button"
            onClick={() => void generate(false)}
            className="mt-2 rounded-md bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-white"
          >
            Generate evidence review
          </button>
        </div>
      ) : null}

      {state === "loading" ? (
        <p role="status" aria-live="polite" aria-busy="true" className="mt-3 text-sm text-slate-200">
          Generating evidence review…
        </p>
      ) : null}

      {state === "unavailable" || state === "error" || state === "rate-limited" || state === "blocked" ? (
        <div className="mt-3 rounded border border-slate-700 p-3" role="alert">
          <p className="text-sm font-medium text-slate-100">
            {reviewStatusCopy(state).title}
          </p>
          <p className="mt-1 text-sm text-slate-300">{review?.message ?? reviewStatusCopy(state).message}</p>
          {detail ? (
            <pre className="mt-2 max-h-32 overflow-auto whitespace-pre-wrap text-xs text-slate-400">
              {detail}
            </pre>
          ) : null}
          {state === "error" || state === "rate-limited" ? (
            <button
              type="button"
              onClick={() => void generate(false)}
              className="mt-2 rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-800"
            >
              Retry
            </button>
          ) : null}
        </div>
      ) : null}

      {state === "available" && review?.sections ? (
        <div className="mt-3 flex flex-col gap-4">
          <p className="text-xs text-slate-400">
            Explanatory assistance only — the deterministic assessment above is the source
            of truth.
          </p>
          {REVIEW_SECTION_ORDER.map((key) => (
            <div key={key}>
              <h3 className="text-sm font-semibold text-slate-100">{sectionTitle(key)}</h3>
              <ul className="mt-1 flex flex-col gap-1.5">
                {review.sections?.[key].map((bullet, i) => (
                  <li key={i} className="text-sm text-slate-200">
                    <CitedText text={bullet.text} sources={review.sources} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
          <div>
            <h3 className="text-sm font-semibold text-slate-100">Sources</h3>
            <ul className="mt-1 flex flex-col gap-1">
              {review.sources.map((source) => (
                <li key={source.id} className="text-sm">
                  <span className="font-mono text-xs text-slate-400">{source.id}</span>{" "}
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={`${source.label} (${source.kind}, external link)`}
                    className="text-sky-300 underline"
                  >
                    {source.label}
                  </a>{" "}
                  <span className="text-xs text-slate-400">· {source.kind}</span>
                </li>
              ))}
            </ul>
          </div>
          {canRegenerate(state) ? (
            <div>
              <button
                type="button"
                onClick={() => void generate(true)}
                className="rounded border border-slate-600 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-800"
              >
                Regenerate evidence review
              </button>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
