"""Evidence-grounded change review endpoint (Stage 7). Backend-only providers."""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Literal, cast

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from api import github_client
from api.github_client import (
    PublicDataError,
    PublicDataNotFound,
    PublicDataRateLimited,
)
from api.public_data import build_assessment
from hollow_green import evidence_review as er

logger = logging.getLogger(__name__)

REVIEW_TIMEOUT = httpx.Timeout(20.0, connect=10.0)
REVIEW_MAX_TOKENS = 1500

SETUP_MESSAGE = (
    "AI review is not configured. Set AI_REVIEW_PROVIDER, AI_REVIEW_BASE_URL, "
    "AI_REVIEW_MODEL, and AI_REVIEW_API_KEY on the server to enable it. "
    "The deterministic assessment and source evidence remain available."
)
BLOCKED_MESSAGE = (
    "The AI response did not meet evidence-grounding requirements. "
    "The deterministic assessment and source evidence remain available."
)
PROVIDER_ERROR_MESSAGE = (
    "The evidence review provider is unavailable. "
    "The deterministic assessment and source evidence remain available."
)
AI_LIMITATION = "AI output is explanatory assistance; review cited sources before acting."

review_router = APIRouter()


class ProviderError(Exception):
    """Sanitized provider failure. Category only; never carries secrets or payloads."""

    def __init__(self, category: str):
        super().__init__(category)
        self.category = category


class EvidenceReviewProvider(ABC):
    """Backend-only review provider. The frontend is never bound to a vendor."""

    name: str = "base"

    @abstractmethod
    def is_configured(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def generate(self, bundle: er.EvidenceBundle, system: str, user: str) -> dict[str, object]:
        raise NotImplementedError


class NoProvider(EvidenceReviewProvider):
    name = "none"

    def is_configured(self) -> bool:
        return False

    def generate(self, bundle: er.EvidenceBundle, system: str, user: str) -> dict[str, object]:
        raise ProviderError("config")


class OpenAICompatibleProvider(EvidenceReviewProvider):
    name = "openai_compatible"

    def __init__(self, base_url: str, model: str, api_key: str):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key

    @classmethod
    def from_env(cls) -> "OpenAICompatibleProvider | None":
        if os.environ.get("AI_REVIEW_PROVIDER", "").strip() != "openai_compatible":
            return None
        base_url = os.environ.get("AI_REVIEW_BASE_URL", "").strip()
        model = os.environ.get("AI_REVIEW_MODEL", "").strip()
        api_key = os.environ.get("AI_REVIEW_API_KEY", "").strip()
        if not base_url or not model or not api_key:
            return None
        return cls(base_url=base_url, model=model, api_key=api_key)

    def is_configured(self) -> bool:
        return True

    def generate(self, bundle: er.EvidenceBundle, system: str, user: str) -> dict[str, object]:
        payload: dict[str, object] = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": REVIEW_MAX_TOKENS,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        url = self.base_url.rstrip("/") + "/chat/completions"
        # The key lives only in this local header mapping; it is never logged.
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        try:
            response = httpx.post(url, json=payload, headers=headers, timeout=REVIEW_TIMEOUT)
        except httpx.TimeoutException as exc:
            raise ProviderError("timeout") from exc
        except httpx.HTTPError as exc:
            raise ProviderError("transport") from exc
        if response.status_code != 200:
            if 400 <= response.status_code < 500:
                raise ProviderError("http_client")
            raise ProviderError("http_server")
        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderError("malformed") from exc
        content = _extract_content(data)
        if not content:
            raise ProviderError("malformed")
        if len(content) > er.MAX_RESPONSE_CHARS:
            raise ProviderError("too_large")
        try:
            parsed = json.loads(content)
        except ValueError as exc:
            raise ProviderError("malformed") from exc
        if not isinstance(parsed, dict):
            raise ProviderError("malformed")
        return cast(dict[str, object], parsed)


def _extract_content(data: object) -> str:
    if not isinstance(data, dict):
        return ""
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0]
    if not isinstance(first, dict):
        return ""
    message = first.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    return content if isinstance(content, str) else ""


def resolve_provider() -> EvidenceReviewProvider:
    """Return the configured provider, or NoProvider when nothing is configured."""
    configured_name = os.environ.get("AI_REVIEW_PROVIDER", "").strip()
    if configured_name and configured_name != "openai_compatible":
        raise ProviderError("config")
    provider = OpenAICompatibleProvider.from_env()
    if provider is not None:
        return provider
    return NoProvider()


def get_review_provider() -> EvidenceReviewProvider:
    return resolve_provider()


class EvidenceReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regenerate: bool = False


class AssessmentIdentity(BaseModel):
    owner: str
    repo: str
    candidate: str
    retrieved_at: str
    served_from: str


class DeterministicEcho(BaseModel):
    change_risk_level: str
    evidence_completeness: str
    deployment_readiness: str
    public_recommendation: str


class ReviewBulletOut(BaseModel):
    text: str
    citation_ids: list[str] = Field(default_factory=list)


class ReviewSectionsOut(BaseModel):
    evidence_summary: list[ReviewBulletOut]
    deterministic_assessment_explanation: list[ReviewBulletOut]
    evidence_gaps: list[ReviewBulletOut]
    human_review_checks: list[ReviewBulletOut]


class ReviewSourceOut(BaseModel):
    id: str
    label: str
    url: str
    kind: str


class EvidenceReviewResponse(BaseModel):
    status: Literal["available", "unavailable", "error", "blocked"]
    provider_configured: bool
    generated_at: str | None = None
    message: str | None = None
    assessment_identity: AssessmentIdentity | None = None
    deterministic_assessment: DeterministicEcho | None = None
    sections: ReviewSectionsOut | None = None
    sources: list[ReviewSourceOut] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


def _as_stale(cached: dict[str, object], live_error: str) -> dict[str, object]:
    stale = dict(cached)
    stale["served_from"] = "stale_cache"
    limitations = cached.get("limitations")
    items = list(limitations) if isinstance(limitations, list) else []
    items.append(f"Live GitHub refresh failed ({live_error}); showing last saved assessment.")
    stale["limitations"] = items
    return stale


def load_review_assessment(
    owner: str,
    repo: str,
    candidate: str,
    refresh: bool,
    fixture: bool,
) -> dict[str, object]:
    """Load the normalized assessment with established cache/fixture semantics.

    Never touches ReleaseLog or analyze_log. Supports stale_cache fallback.
    """
    repo_full_name = f"{owner}/{repo}"
    try:
        github_client.validate_repo(repo_full_name)
    except PublicDataNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    cache_key = f"{repo_full_name}|{candidate or 'default'}"
    if fixture:
        try:
            raw = github_client.load_fixture_evidence(owner, repo)
        except PublicDataNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        try:
            return build_assessment(raw, owner, repo, "fixture", candidate or None)
        except PublicDataNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not refresh:
        peeked = github_client.peek_cache(cache_key)
        if peeked is not None:
            age_seconds, cached = peeked
            if age_seconds <= github_client.CACHE_TTL_SECONDS:
                return cached
    try:
        raw = github_client.fetch_live_evidence(owner, repo)
    except PublicDataRateLimited as exc:
        peeked = github_client.peek_cache(cache_key)
        if peeked is not None:
            _, cached = peeked
            if _is_fresh(peeked[0]):
                return cached
            return _as_stale(cached, str(exc))
        try:
            raw_fixture = github_client.load_fixture_evidence(owner, repo)
            return build_assessment(
                raw_fixture, owner, repo, "fixture", candidate or None, live_error=str(exc)
            )
        except PublicDataNotFound:
            pass
        detail: object = {"message": str(exc)}
        if exc.reset_at:
            detail = {"message": str(exc), "rate_limit_reset": exc.reset_at}
        raise HTTPException(status_code=429, detail=detail) from exc
    except PublicDataError as exc:
        peeked = github_client.peek_cache(cache_key)
        if peeked is not None:
            _, cached = peeked
            if _is_fresh(peeked[0]):
                return cached
            return _as_stale(cached, str(exc))
        try:
            raw_fixture = github_client.load_fixture_evidence(owner, repo)
            return build_assessment(
                raw_fixture, owner, repo, "fixture", candidate or None, live_error=str(exc)
            )
        except PublicDataNotFound:
            pass
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    try:
        assessment = build_assessment(raw, owner, repo, "live", candidate or None)
    except PublicDataNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    github_client.set_cached(cache_key, assessment)
    return assessment


def _is_fresh(age_seconds: float) -> bool:
    return age_seconds <= github_client.CACHE_TTL_SECONDS


def _identity(owner: str, repo: str, assessment: dict[str, object]) -> AssessmentIdentity:
    candidate_raw = assessment.get("candidate")
    candidate_id = ""
    if isinstance(candidate_raw, dict):
        raw_id = candidate_raw.get("candidate_id")
        candidate_id = raw_id if isinstance(raw_id, str) else ""
    retrieved = assessment.get("retrieved_at")
    served = assessment.get("served_from")
    return AssessmentIdentity(
        owner=owner,
        repo=repo,
        candidate=candidate_id,
        retrieved_at=retrieved if isinstance(retrieved, str) else "",
        served_from=served if isinstance(served, str) else "",
    )


def _echo(assessment: dict[str, object]) -> DeterministicEcho:
    result = assessment.get("public_result")
    fields: dict[str, str] = {}
    if isinstance(result, dict):
        for key in (
            "change_risk_level",
            "evidence_completeness",
            "deployment_readiness",
            "public_recommendation",
        ):
            value = result.get(key)
            fields[key] = value if isinstance(value, str) else ""
    else:
        fields = {
            "change_risk_level": "",
            "evidence_completeness": "",
            "deployment_readiness": "",
            "public_recommendation": "",
        }
    return DeterministicEcho(**fields)


def _limitations(assessment: dict[str, object], extra: str | None = None) -> list[str]:
    raw = assessment.get("limitations")
    items = [str(i) for i in raw] if isinstance(raw, list) else []
    if extra:
        items.append(extra)
    return items


@review_router.post(
    "/v1/public-data/assessments/{owner}/{repo}/{candidate}/evidence-review",
    response_model=EvidenceReviewResponse,
    description="Generate an evidence-grounded review of a public-data assessment.",
)
def post_evidence_review(
    owner: str,
    repo: str,
    candidate: str,
    body: EvidenceReviewRequest,
    refresh: bool = Query(default=False),
    fixture: bool = Query(default=False),
) -> EvidenceReviewResponse:
    logger.info("evidence_review requested regenerate=%s", body.regenerate)
    assessment = load_review_assessment(owner, repo, candidate, refresh, fixture)
    identity = _identity(owner, repo, assessment)
    echo = _echo(assessment)
    try:
        provider = get_review_provider()
    except ProviderError:
        return EvidenceReviewResponse(
            status="error",
            provider_configured=False,
            generated_at=datetime.now(UTC).isoformat(),
            message="Evidence review provider configuration is not supported.",
            assessment_identity=identity,
            deterministic_assessment=echo,
            limitations=_limitations(assessment),
        )
    if not provider.is_configured():
        return EvidenceReviewResponse(
            status="unavailable",
            provider_configured=False,
            generated_at=datetime.now(UTC).isoformat(),
            message=SETUP_MESSAGE,
            assessment_identity=identity,
            deterministic_assessment=echo,
            limitations=_limitations(assessment, SETUP_MESSAGE),
        )
    try:
        bundle = er.build_evidence_bundle(assessment)
        system, user = er.build_review_prompt(bundle)
        draft = provider.generate(bundle, system, user)
    except er.BundleError as exc:
        raise HTTPException(status_code=502, detail=PROVIDER_ERROR_MESSAGE) from exc
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=PROVIDER_ERROR_MESSAGE) from exc
    issues = er.validate_review_output(draft, bundle)
    if issues:
        return EvidenceReviewResponse(
            status="blocked",
            provider_configured=True,
            generated_at=datetime.now(UTC).isoformat(),
            message=BLOCKED_MESSAGE,
            assessment_identity=identity,
            deterministic_assessment=echo,
            limitations=_limitations(assessment, AI_LIMITATION),
        )
    by_id = {r.id: r for r in bundle.records}
    return EvidenceReviewResponse(
        status="available",
        provider_configured=True,
        generated_at=datetime.now(UTC).isoformat(),
        assessment_identity=identity,
        deterministic_assessment=echo,
        sections=_to_sections(draft),
        sources=_to_sources(draft, by_id),
        limitations=_limitations(assessment, AI_LIMITATION),
    )


def _to_sections(draft: dict[str, object]) -> ReviewSectionsOut:
    sections_raw = draft.get("sections")
    if not isinstance(sections_raw, dict):
        raise ProviderError("malformed")
    converted: dict[str, list[ReviewBulletOut]] = {}
    for key in er.SECTION_KEYS:
        bullets_raw = sections_raw.get(key)
        if not isinstance(bullets_raw, list):
            raise ProviderError("malformed")
        items: list[ReviewBulletOut] = []
        for bullet in bullets_raw:
            if not isinstance(bullet, dict):
                raise ProviderError("malformed")
            text = bullet.get("text")
            citations = bullet.get("citation_ids", [])
            if not isinstance(text, str) or not isinstance(citations, list):
                raise ProviderError("malformed")
            ids = [c for c in citations if isinstance(c, str)]
            items.append(ReviewBulletOut(text=text, citation_ids=ids))
        converted[key] = items
    return ReviewSectionsOut(**converted)


def _to_sources(
    draft: dict[str, object], by_id: dict[str, er.BundleSourceRecord]
) -> list[ReviewSourceOut]:
    sources_raw = draft.get("sources")
    if not isinstance(sources_raw, list):
        raise ProviderError("malformed")
    out: list[ReviewSourceOut] = []
    for source in sources_raw:
        if not isinstance(source, dict):
            raise ProviderError("malformed")
        source_id = source.get("id")
        if not isinstance(source_id, str) or source_id not in by_id:
            raise ProviderError("malformed")
        original = by_id[source_id]
        out.append(
            ReviewSourceOut(
                id=original.id, label=original.label, url=original.url, kind=original.kind
            )
        )
    return out
