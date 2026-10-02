"""Public GitHub evidence routes: list repos + refresh/get assessment."""

from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query

from api import github_client
from api.github_client import (
    PublicDataError,
    PublicDataNotFound,
    PublicDataRateLimited,
)
from hollow_green.public_data import (
    BASE_LIMITATIONS,
    DATA_SOURCE,
    DISCLAIMER,
    UNAVAILABLE_SIGNALS,
    CandidateInfo,
    CommitRef,
    IssueRef,
    PullRef,
    RepositoryEvidence,
    compute_public_result,
    sanitize_id,
    select_candidate,
)

public_router = APIRouter()


@public_router.get(
    "/v1/public-repos",
    description="List allowlisted public GitHub repositories for evidence mode.",
)
def list_public_repos() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for full_name in github_client.allowed_repos():
        items.append(
            {
                "repo_full_name": full_name,
                "display_name": github_client.repo_display_name(full_name),
                "repo_url": github_client.repo_url(full_name),
            }
        )
    return items


def _as_list(value: object) -> list[dict[str, object]]:
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []


def _parse_commit_ref(item: dict[str, object]) -> CommitRef | None:
    sha = item.get("sha")
    if not isinstance(sha, str) or not sha:
        return None
    url = item.get("html_url")
    message = ""
    date = None
    inner = item.get("commit")
    if isinstance(inner, dict):
        raw_message = inner.get("message")
        if isinstance(raw_message, str):
            message = raw_message.split("\n", 1)[0][:160]
        author = inner.get("author")
        if isinstance(author, dict) and isinstance(author.get("date"), str):
            try:
                date = datetime.fromisoformat(str(author["date"]).replace("Z", "+00:00"))
            except ValueError:
                date = None
    return CommitRef(
        sha=sha,
        message=message,
        date=date,
        url=str(url) if isinstance(url, str) and url else f"https://github.com/commit/{sha}",
    )


def _parse_pull_ref(item: dict[str, object]) -> PullRef | None:
    number = item.get("number")
    url = item.get("html_url")
    if not isinstance(number, int) or not isinstance(url, str):
        return None
    title = item.get("title")
    state = item.get("state")
    return PullRef(
        number=number,
        title=str(title) if isinstance(title, str) else "",
        state=str(state) if isinstance(state, str) else "",
        url=url,
    )


def _parse_issue_ref(item: dict[str, object]) -> IssueRef | None:
    number = item.get("number")
    url = item.get("html_url")
    if not isinstance(number, int) or not isinstance(url, str):
        return None
    if isinstance(item.get("pull_request"), dict):
        return None
    title = item.get("title")
    return IssueRef(
        number=number,
        title=str(title) if isinstance(title, str) else "",
        url=url,
    )


def _candidates_available(
    releases: list[dict[str, object]],
    tags: list[dict[str, object]],
    repo_url: str,
) -> list[CandidateInfo]:
    out: list[CandidateInfo] = []
    for rel in releases[:5]:
        if rel.get("draft") is True:
            continue
        tag = str(rel.get("tag_name") or rel.get("name") or "").strip()
        if not tag:
            continue
        url = str(rel.get("html_url") or repo_url)
        out.append(
            CandidateInfo(
                candidate_id=sanitize_id(tag),
                kind="release",
                name=str(rel.get("name") or tag),
                published_at=None,
                url=url,
            )
        )
    for tag_item in tags[:5]:
        name = str(tag_item.get("name") or "").strip()
        if not name:
            continue
        if any(c.candidate_id == sanitize_id(name) for c in out):
            continue
        out.append(
            CandidateInfo(
                candidate_id=sanitize_id(name),
                kind="tag",
                name=name,
                published_at=None,
                url=repo_url,
            )
        )
    return out[:10]


def build_assessment(
    raw: dict[str, object],
    owner: str,
    repo: str,
    served_from: str,
    requested_candidate: str | None = None,
    live_error: str | None = None,
) -> dict[str, object]:
    repo_full_name = f"{owner}/{repo}"
    repo_data = raw.get(f"/repos/{owner}/{repo}")
    repo_meta: dict[str, object] = repo_data if isinstance(repo_data, dict) else {}
    releases = _as_list(raw.get(f"/repos/{owner}/{repo}/releases"))
    tags = _as_list(raw.get(f"/repos/{owner}/{repo}/tags"))
    commits_raw = _as_list(raw.get(f"/repos/{owner}/{repo}/commits"))
    pulls_raw = _as_list(raw.get(f"/repos/{owner}/{repo}/pulls"))
    issues_raw = _as_list(raw.get(f"/repos/{owner}/{repo}/issues"))
    repo_url = str(repo_meta.get("html_url") or github_client.repo_url(repo_full_name))
    default_branch = str(repo_meta.get("default_branch") or "main")
    stars = repo_meta.get("stargazers_count")
    open_count = repo_meta.get("open_issues_count")

    candidate = select_candidate(releases, tags, commits_raw, repo_url)
    if candidate.kind == "none":
        raise PublicDataNotFound(f"no release candidates found for {repo_full_name}")
    if requested_candidate:
        wanted = sanitize_id(requested_candidate)
        available = _candidates_available(releases, tags, repo_url)
        match = next((c for c in available if c.candidate_id == wanted), None)
        if match is None:
            match = next(
                (c for c in available if sanitize_id(c.name) == wanted),
                None,
            )
        if match is None:
            raise PublicDataNotFound(
                f"unknown candidate '{requested_candidate}' for {repo_full_name}"
            )
        resolved_releases = [
            r
            for r in releases
            if sanitize_id(str(r.get("tag_name") or r.get("name") or "")) == match.candidate_id
        ]
        resolved_tags = [
            t for t in tags if sanitize_id(str(t.get("name") or "")) == match.candidate_id
        ]
        candidate = select_candidate(
            resolved_releases
            or (
                [{"tag_name": match.name, "name": match.name, "html_url": match.url}]
                if match.kind != "commit"
                else []
            ),
            resolved_tags,
            commits_raw,
            repo_url,
        )
        if candidate.kind == "none":
            candidate = match

    commits = [c for c in (_parse_commit_ref(i) for i in commits_raw[:5]) if c is not None]
    pulls = [p for p in (_parse_pull_ref(i) for i in pulls_raw[:5]) if p is not None]
    issues = [x for x in (_parse_issue_ref(i) for i in issues_raw[:5]) if x is not None]

    retrieved_raw = raw.get("retrieved_at")
    retrieved_at = datetime.now(UTC)
    if isinstance(retrieved_raw, str):
        try:
            retrieved_at = datetime.fromisoformat(retrieved_raw.replace("Z", "+00:00"))
        except ValueError:
            retrieved_at = datetime.now(UTC)

    sources_raw = raw.get("source_urls")
    source_urls = [str(s) for s in sources_raw] if isinstance(sources_raw, list) else []

    evidence = RepositoryEvidence(
        repo_full_name=repo_full_name,
        repo_url=repo_url,
        default_branch=default_branch,
        stars=int(stars) if isinstance(stars, int) else 0,
        open_issues_count=int(open_count) if isinstance(open_count, int) else 0,
        candidate=candidate,
        candidates_available=_candidates_available(releases, tags, repo_url),
        commits_recent=commits,
        pulls_recent=pulls,
        issues_open_sample=issues,
        retrieved_at=retrieved_at,
        source_urls=source_urls,
    )
    public_result = compute_public_result(evidence)

    limitations = list(BASE_LIMITATIONS)
    limitations.append(f"Served from: {served_from}.")
    limitations.append(f"Candidate: {candidate.kind} '{candidate.name}'.")
    if live_error:
        limitations.append(f"Live GitHub fetch failed ({live_error}); serving saved data.")
    if served_from == "fixture":
        limitations.append("Saved fixture data; refresh from GitHub for live evidence.")

    return {
        "data_source": DATA_SOURCE,
        "served_from": served_from,
        "repo_full_name": repo_full_name,
        "candidate": candidate.model_dump(mode="json"),
        "retrieved_at": retrieved_at.isoformat(),
        "source_urls": source_urls,
        "limitations": limitations,
        "unavailable_signals": list(UNAVAILABLE_SIGNALS),
        "disclaimer": DISCLAIMER,
        "public_result": public_result.model_dump(mode="json"),
        "evidence": evidence.model_dump(mode="json"),
    }


@public_router.get(
    "/v1/public-repos/{owner}/{repo}/assessment",
    description="Get or refresh a public GitHub evidence assessment for an allowlisted repo.",
)
def get_public_assessment(
    owner: str,
    repo: str,
    candidate: str | None = Query(default=None),
    refresh: bool = Query(default=False),
    fixture: bool = Query(default=False),
) -> dict[str, object]:
    repo_full_name = f"{owner}/{repo}"
    try:
        github_client.validate_repo(repo_full_name)
    except PublicDataNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    cache_key = f"{repo_full_name}|{candidate or 'default'}"
    use_fixture = fixture or (
        github_client.fixture_only_enabled() and github_client.has_fixture(owner, repo)
    )
    if use_fixture:
        try:
            raw = github_client.load_fixture_evidence(owner, repo)
        except PublicDataNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        try:
            return build_assessment(raw, owner, repo, "fixture", candidate)
        except PublicDataNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not refresh:
        cached = github_client.get_cached(cache_key)
        if cached is not None:
            return cached
    try:
        raw = github_client.fetch_live_evidence(owner, repo)
    except PublicDataRateLimited as exc:
        cached = github_client.get_cached(cache_key)
        if cached is not None:
            return cached
        try:
            raw_fixture = github_client.load_fixture_evidence(owner, repo)
            return build_assessment(
                raw_fixture, owner, repo, "fixture", candidate, live_error=str(exc)
            )
        except PublicDataNotFound:
            pass
        detail: object = {"message": str(exc)}
        if exc.reset_at:
            detail = {"message": str(exc), "rate_limit_reset": exc.reset_at}
        raise HTTPException(status_code=429, detail=detail) from exc
    except PublicDataError as exc:
        cached = github_client.get_cached(cache_key)
        if cached is not None:
            return cached
        try:
            raw_fixture = github_client.load_fixture_evidence(owner, repo)
            return build_assessment(
                raw_fixture, owner, repo, "fixture", candidate, live_error=str(exc)
            )
        except PublicDataNotFound:
            pass
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    try:
        assessment = build_assessment(raw, owner, repo, "live", candidate)
    except PublicDataNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    github_client.set_cached(cache_key, assessment)
    return assessment
