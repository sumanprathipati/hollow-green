"""Backend-only GitHub REST client. Never expose tokens to the frontend."""

import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx

API_BASE = "https://api.github.com"
TIMEOUT_SECONDS = 10.0
CACHE_TTL_SECONDS = 300

REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")

DEFAULT_ALLOWLIST = ["octocat/Hello-World"]

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "github"


class PublicDataError(Exception):
    status_code: int = 502

    def __init__(self, message: str):
        super().__init__(message)


class PublicDataNotFound(PublicDataError):
    status_code = 404


class PublicDataRateLimited(PublicDataError):
    status_code = 429

    def __init__(self, message: str, reset_at: str | None = None):
        super().__init__(message)
        self.reset_at = reset_at


class PublicDataUnavailable(PublicDataError):
    status_code = 502


def get_github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    return token or None


def fixture_only_enabled() -> bool:
    """Test-only mode for deterministic E2E/dev runs. Never enabled by default."""
    return os.environ.get("PUBLIC_DATA_FIXTURE_ONLY", "") == "1"


def allowed_repos() -> list[str]:
    raw = os.environ.get("PUBLIC_REPOS", "").strip()
    if not raw:
        return list(DEFAULT_ALLOWLIST)
    repos = [r.strip() for r in raw.split(",") if r.strip()]
    return repos or list(DEFAULT_ALLOWLIST)


def repo_display_name(repo_full_name: str) -> str:
    return repo_full_name


def repo_url(repo_full_name: str) -> str:
    return f"https://github.com/{repo_full_name}"


def validate_repo(repo_full_name: str) -> tuple[str, str]:
    if not REPO_PATTERN.match(repo_full_name):
        raise PublicDataNotFound(f"unknown public repository: {repo_full_name}")
    if repo_full_name not in allowed_repos():
        raise PublicDataNotFound(f"unknown public repository: {repo_full_name}")
    owner, name = repo_full_name.split("/", 1)
    return owner, name


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "hollow-green",
    }
    token = get_github_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(path: str, params: dict[str, str | int] | None = None) -> tuple[object, str]:
    url = f"{API_BASE}{path}"
    try:
        response = httpx.get(url, params=params, headers=_headers(), timeout=TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise PublicDataUnavailable(f"github request failed: {exc}") from exc
    source = str(response.request.url)
    if response.status_code == 404:
        raise PublicDataNotFound(f"github resource not found: {path}")
    if response.status_code == 403 or response.status_code == 429:
        remaining = response.headers.get("x-ratelimit-remaining")
        reset = response.headers.get("x-ratelimit-reset")
        if response.status_code == 403 and remaining not in (None, "0"):
            raise PublicDataUnavailable(f"github forbidden for {path}")
        raise PublicDataRateLimited("github rate limit exceeded", reset_at=reset)
    if response.status_code >= 400:
        raise PublicDataUnavailable(f"github request failed ({response.status_code}) for {path}")
    try:
        return response.json(), source
    except ValueError as exc:
        raise PublicDataUnavailable("github returned invalid json") from exc


def fetch_live_evidence(owner: str, repo: str) -> dict[str, object]:
    repo_full_name = f"{owner}/{repo}"
    queries: list[tuple[str, dict[str, str | int] | None]] = [
        (f"/repos/{owner}/{repo}", None),
        (f"/repos/{owner}/{repo}/releases", {"per_page": 5}),
        (f"/repos/{owner}/{repo}/tags", {"per_page": 5}),
        (f"/repos/{owner}/{repo}/commits", {"per_page": 5}),
        (
            f"/repos/{owner}/{repo}/pulls",
            {"state": "all", "per_page": 5, "sort": "updated", "direction": "desc"},
        ),
        (f"/repos/{owner}/{repo}/issues", {"state": "open", "per_page": 5}),
    ]
    payload: dict[str, object] = {"repo_full_name": repo_full_name}
    sources: list[str] = []
    for path, params in queries:
        data, source = github_get(path, params)
        payload[path] = data
        sources.append(source)
    payload["source_urls"] = sources
    payload["retrieved_at"] = datetime.now(UTC).isoformat()
    return payload


def fixture_path(owner: str, repo: str) -> Path:
    return (FIXTURE_DIR / f"{owner}__{repo}.json").resolve()


def has_fixture(owner: str, repo: str) -> bool:
    target = fixture_path(owner, repo)
    return target.parent == FIXTURE_DIR.resolve() and target.is_file()


def load_fixture_evidence(owner: str, repo: str) -> dict[str, object]:
    target = fixture_path(owner, repo)
    base = FIXTURE_DIR.resolve()
    if target.parent != base or not target.is_file():
        raise PublicDataNotFound(f"no saved fixture for {owner}/{repo}")
    data: dict[str, object] = json.loads(target.read_text())
    return data


_cache: dict[str, tuple[datetime, dict[str, object]]] = {}


def get_cached(key: str) -> dict[str, object] | None:
    entry = _cache.get(key)
    if not entry:
        return None
    stored_at, value = entry
    if datetime.now(UTC) - stored_at > timedelta(seconds=CACHE_TTL_SECONDS):
        _cache.pop(key, None)
        return None
    return value


def set_cached(key: str, value: dict[str, object]) -> None:
    _cache[key] = (datetime.now(UTC), value)


def peek_cache(key: str) -> tuple[float, dict[str, object]] | None:
    """Return (age_seconds, value) without evicting expired entries."""
    entry = _cache.get(key)
    if not entry:
        return None
    stored_at, value = entry
    age_seconds = (datetime.now(UTC) - stored_at).total_seconds()
    return age_seconds, value


def clear_cache() -> None:
    _cache.clear()
