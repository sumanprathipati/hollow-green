"""Public GitHub evidence schemas + explicit mapping to the ReleaseLog input model.

No scoring here. Mapping is deterministic and conservative: only directly
observable public signals become engine events. Everything else is
unavailable / unknown and listed in limitations.
"""

import re
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from hollow_green.schemas import ReleaseLog

DATA_SOURCE = "public-github"
DISCLAIMER = "Public repository evidence only — not a production deployment decision."
HERO_SENTENCE = "Public repository evidence only — deployment readiness cannot be determined."

DEPLOYMENT_READINESS = "not_assessable_from_public_data"

UNAVAILABLE_SIGNALS: list[str] = [
    "health",
    "rollback",
    "ci",
    "retry_consumption",
    "manual_interventions",
    "production_telemetry",
]

BASE_LIMITATIONS: list[str] = [
    HERO_SENTENCE,
    DISCLAIMER,
    "Change activity is observed from public commits, pull requests, releases/tags, "
    "and open issues only.",
    "Health, rollback, CI, retries, manual interventions, and production telemetry "
    "are unavailable from public data and are not inferred.",
    "Candidate dates are publication dates, not deployment times.",
]

WINDOW_MINUTES_DEFAULT = 60
RETRY_BUDGET_DEFAULT = 5


class EvidenceLink(BaseModel):
    label: str = Field(min_length=1)
    url: str = Field(min_length=1)


class CandidateInfo(BaseModel):
    candidate_id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    name: str = Field(min_length=1)
    published_at: datetime | None = None
    url: str = Field(min_length=1)


class CommitRef(BaseModel):
    sha: str = Field(min_length=1)
    message: str = ""
    date: datetime | None = None
    url: str = Field(min_length=1)


class PullRef(BaseModel):
    number: int
    title: str = ""
    state: str = ""
    url: str = Field(min_length=1)


class IssueRef(BaseModel):
    number: int
    title: str = ""
    url: str = Field(min_length=1)


class RepositoryEvidence(BaseModel):
    repo_full_name: str = Field(min_length=1)
    repo_url: str = Field(min_length=1)
    default_branch: str = "main"
    stars: int = 0
    open_issues_count: int = 0
    candidate: CandidateInfo
    candidates_available: list[CandidateInfo] = Field(default_factory=list)
    commits_recent: list[CommitRef] = Field(default_factory=list)
    pulls_recent: list[PullRef] = Field(default_factory=list)
    issues_open_sample: list[IssueRef] = Field(default_factory=list)
    retrieved_at: datetime
    source_urls: list[str] = Field(default_factory=list)


class PublicResult(BaseModel):
    change_risk_level: str = Field(pattern="^(low|moderate|elevated|unknown)$")
    evidence_completeness: str = Field(pattern="^(sufficient|limited|insufficient)$")
    deployment_readiness: str = DEPLOYMENT_READINESS
    public_recommendation: str = ""
    reasons: list[str] = Field(default_factory=list)


class PublicDataAssessment(BaseModel):
    data_source: str = DATA_SOURCE
    served_from: str = "live"
    repo_full_name: str = Field(min_length=1)
    candidate: CandidateInfo
    retrieved_at: datetime
    source_urls: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    unavailable_signals: list[str] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
    public_result: PublicResult
    evidence: RepositoryEvidence


def compute_public_result(evidence: RepositoryEvidence) -> PublicResult:
    """Public-only risk vocabulary, computed solely from observable public data.

    Missing operational signals affect completeness; they are never treated as
    negative release-health events. No scoring engine, window, or retry-budget
    assumptions are used here.
    """

    def _as_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    ref_date = evidence.candidate.published_at
    commit_dates = [c.date for c in evidence.commits_recent if c.date is not None]
    if ref_date is None and commit_dates:
        ref_date = max(commit_dates)
    age_days: int | None = None
    if ref_date is not None:
        delta = _as_aware(evidence.retrieved_at) - _as_aware(ref_date)
        age_days = max(0, int(delta.total_seconds() // 86400))
    commit_count = len(evidence.commits_recent)
    open_prs = [p for p in evidence.pulls_recent if p.state == "open"]
    any_pr_activity = len(evidence.pulls_recent) > 0
    open_issues = evidence.open_issues_count
    has_candidate = evidence.candidate.kind != "none"
    dated = evidence.candidate.published_at is not None or len(commit_dates) > 0

    reasons: list[str] = []
    if has_candidate:
        reasons.append(f"candidate: {evidence.candidate.kind} '{evidence.candidate.name}'")
    else:
        reasons.append("no release/tag/commit candidate found")
    reasons.append(f"observed commits: {commit_count}")
    reasons.append(f"open pull requests observed: {len(open_prs)}")
    reasons.append(f"open issues reported: {open_issues}")
    reasons.append(
        f"candidate age days: {age_days}" if age_days is not None else "candidate age: unknown"
    )

    if not has_candidate or (commit_count == 0 and not any_pr_activity and not dated):
        completeness = "insufficient"
    elif (
        has_candidate
        and dated
        and commit_count > 0
        and (any_pr_activity or len(evidence.issues_open_sample) > 0)
    ):
        completeness = "sufficient"
    else:
        completeness = "limited"

    if completeness == "insufficient":
        risk = "unknown"
    elif (
        (age_days is not None and age_days <= 7)
        or commit_count >= 4
        or len(open_prs) >= 1
        or open_issues >= 5
    ):
        risk = "elevated"
    elif (
        (age_days is not None and age_days <= 30)
        or commit_count >= 2
        or any_pr_activity
        or open_issues >= 1
    ):
        risk = "moderate"
    else:
        risk = "low"

    if risk == "low":
        recommendation = "LOWER CHANGE RISK — REVIEW REQUIRED"
    elif risk == "moderate":
        recommendation = "MODERATE CHANGE RISK — REVIEW EVIDENCE"
    elif risk == "elevated":
        recommendation = "ELEVATED CHANGE RISK — INVESTIGATE"
    else:
        recommendation = "INSUFFICIENT EVIDENCE — DO NOT INFER READINESS"

    return PublicResult(
        change_risk_level=risk,
        evidence_completeness=completeness,
        deployment_readiness=DEPLOYMENT_READINESS,
        public_recommendation=recommendation,
        reasons=reasons,
    )


def sanitize_id(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "candidate"


def select_candidate(
    releases: list[dict[str, object]],
    tags: list[dict[str, object]],
    commits: list[dict[str, object]],
    repo_url: str,
) -> CandidateInfo:
    for rel in releases:
        draft = rel.get("draft") is True
        if draft:
            continue
        tag = str(rel.get("tag_name") or rel.get("name") or "").strip()
        if not tag:
            continue
        url = str(rel.get("html_url") or repo_url)
        published = rel.get("published_at") or rel.get("created_at")
        published_at = _parse_dt(published) if isinstance(published, str) else None
        name = str(rel.get("name") or tag)
        return CandidateInfo(
            candidate_id=sanitize_id(tag),
            kind="release",
            name=name,
            published_at=published_at,
            url=url,
        )
    for tag_item in tags:
        name = str(tag_item.get("name") or "").strip()
        if not name:
            continue
        commit = tag_item.get("commit")
        url = repo_url
        if isinstance(commit, dict) and isinstance(commit.get("url"), str):
            url = str(commit["url"])
        return CandidateInfo(
            candidate_id=sanitize_id(name),
            kind="tag",
            name=name,
            published_at=None,
            url=url,
        )
    for commit_item in commits:
        sha = str(commit_item.get("sha") or "").strip()
        if not sha:
            continue
        url = str(commit_item.get("html_url") or repo_url)
        inner = commit_item.get("commit")
        date: datetime | None = None
        if isinstance(inner, dict):
            author = inner.get("author")
            if isinstance(author, dict) and isinstance(author.get("date"), str):
                date = _parse_dt(str(author["date"]))
        return CandidateInfo(
            candidate_id=sanitize_id(sha[:12]),
            kind="commit",
            name=sha[:12],
            published_at=date,
            url=url,
        )
    return CandidateInfo(
        candidate_id="no-candidate",
        kind="none",
        name="no-candidate",
        published_at=None,
        url=repo_url,
    )


def _parse_dt(value: str) -> datetime | None:
    try:
        text = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed
    except ValueError:
        return None


def map_evidence_to_release_log(
    repo_full_name: str,
    candidate: CandidateInfo,
    commits: list[CommitRef],
    repo_url: str,
    retrieved_at: datetime,
) -> ReleaseLog:
    """Isolated internal-only mapping helper.

    Retained for documentation and unit-test coverage of the mapping shape.
    It is NOT used by the public assessment route and its fixed window /
    retry-budget assumptions MUST NOT influence any public-facing assessment.
    """
    release_id = f"github-{sanitize_id(repo_full_name)}-{candidate.candidate_id}"
    service = f"github-{sanitize_id(repo_full_name.split('/')[-1])}-public"
    terminal_ts = candidate.published_at or retrieved_at
    commit_dates = [c.date for c in commits if c.date is not None]
    start_ts = min(commit_dates) if commit_dates else terminal_ts
    if start_ts > terminal_ts:
        start_ts = terminal_ts
    events: list[dict[str, object]] = [
        {
            "event_id": "evt-01",
            "release_id": release_id,
            "ts": start_ts.isoformat(),
            "type": "deploy_started",
            "actor": "system",
            "severity": "info",
            "details": {"source_url": repo_url},
        }
    ]
    for index, commit in enumerate(commits[:5]):
        ts = commit.date or start_ts
        if ts < start_ts:
            ts = start_ts
        if ts > terminal_ts:
            ts = terminal_ts
        events.append(
            {
                "event_id": f"evt-{index + 2:02d}",
                "release_id": release_id,
                "ts": ts.isoformat(),
                "type": "deploy_progress",
                "actor": "system",
                "severity": "info",
                "details": {"sha": commit.sha, "source_url": commit.url},
            }
        )
    terminal_id = f"evt-{len(events) + 1:02d}"
    if terminal_ts <= start_ts and len(events) > 1:
        terminal_ts = start_ts
    events.append(
        {
            "event_id": terminal_id,
            "release_id": release_id,
            "ts": terminal_ts.isoformat(),
            "type": "deploy_succeeded",
            "actor": "pipeline",
            "severity": "info",
            "details": {
                "source_url": candidate.url,
                "candidate": candidate.candidate_id,
            },
        }
    )
    payload_events: list[dict[str, object]] = sorted(events, key=lambda e: str(e["ts"]))
    fixed: list[dict[str, object]] = []
    for index, event in enumerate(payload_events):
        item = dict(event)
        item["event_id"] = f"evt-{index + 1:02d}"
        fixed.append(item)
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "release_id": release_id,
        "service": service,
        "window_minutes": WINDOW_MINUTES_DEFAULT,
        "retry_budget_max": RETRY_BUDGET_DEFAULT,
        "events": fixed,
    }
    return ReleaseLog.model_validate(payload)
