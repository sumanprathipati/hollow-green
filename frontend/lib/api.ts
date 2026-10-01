import type {
  DemoReleaseMeta,
  EvidenceReviewResponse,
  PublicDataAssessment,
  PublicRepoMeta,
  ReleaseLog,
  ReleaseReport,
} from "@/lib/types";

export function apiBaseUrl(): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (fromEnv && fromEnv.length > 0) return fromEnv;
  return "http://127.0.0.1:8000";
}

async function handleJson(res: Response, url: string): Promise<unknown> {
  if (!res.ok) {
    let detail: unknown = null;
    try {
      const body = (await res.json()) as { detail?: unknown };
      detail = body.detail ?? body;
    } catch {
      detail = res.statusText;
    }
    const err = new Error(`Request failed ${res.status} for ${url}`) as Error & {
      status: number;
      detail: unknown;
      url: string;
    };
    err.status = res.status;
    err.detail = detail;
    err.url = url;
    throw err;
  }
  return (await res.json()) as unknown;
}

export async function getDemoReleases(
  base: string = apiBaseUrl(),
): Promise<DemoReleaseMeta[]> {
  const url = `${base}/v1/demo-releases`;
  const res = await fetch(url);
  return (await handleJson(res, url)) as DemoReleaseMeta[];
}

export async function getDemoRelease(
  releaseId: string,
  base: string = apiBaseUrl(),
): Promise<ReleaseLog> {
  const url = `${base}/v1/demo-releases/${encodeURIComponent(releaseId)}`;
  const res = await fetch(url);
  return (await handleJson(res, url)) as ReleaseLog;
}

export async function analyzeRelease(
  log: ReleaseLog,
  base: string = apiBaseUrl(),
): Promise<ReleaseReport> {
  const url = `${base}/v1/releases:analyze`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(log),
  });
  return (await handleJson(res, url)) as ReleaseReport;
}

export async function getPublicRepos(
  base: string = apiBaseUrl(),
): Promise<PublicRepoMeta[]> {
  const url = `${base}/v1/public-repos`;
  const res = await fetch(url);
  return (await handleJson(res, url)) as PublicRepoMeta[];
}

export async function getPublicAssessment(
  repoFullName: string,
  opts: { candidate?: string; refresh?: boolean; fixture?: boolean } = {},
  base: string = apiBaseUrl(),
): Promise<PublicDataAssessment> {
  const [owner, repo] = repoFullName.split("/");
  const params = new URLSearchParams();
  if (opts.candidate) params.set("candidate", opts.candidate);
  if (opts.refresh) params.set("refresh", "true");
  if (opts.fixture) params.set("fixture", "true");
  const qs = params.toString();
  const url = `${base}/v1/public-repos/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/assessment${qs ? `?${qs}` : ""}`;
  const res = await fetch(url);
  return (await handleJson(res, url)) as PublicDataAssessment;
}

export async function requestEvidenceReview(
  owner: string,
  repo: string,
  candidate: string,
  opts: { refresh?: boolean; fixture?: boolean; regenerate?: boolean } = {},
  base: string = apiBaseUrl(),
): Promise<EvidenceReviewResponse> {
  const params = new URLSearchParams();
  if (opts.refresh) params.set("refresh", "true");
  if (opts.fixture) params.set("fixture", "true");
  const qs = params.toString();
  const url = `${base}/v1/public-data/assessments/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}/${encodeURIComponent(candidate)}/evidence-review${qs ? `?${qs}` : ""}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ regenerate: opts.regenerate ?? false }),
  });
  return (await handleJson(res, url)) as EvidenceReviewResponse;
}
