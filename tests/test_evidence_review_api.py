"""Evidence-review endpoint tests. No live GitHub or provider calls."""

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient

from api import evidence_review as api_review
from api import github_client
from api.evidence_review import EvidenceReviewProvider
from api.main import create_app
from api.public_data import build_assessment
from hollow_green import evidence_review as er

client = TestClient(create_app())
FIXTURE = Path(__file__).parent / "fixtures" / "github" / "octocat__Hello-World.json"
REVIEW_URL = "/v1/public-data/assessments/octocat/Hello-World/v1-0/evidence-review"


@pytest.fixture(autouse=True)
def clean_env_cache(monkeypatch):
    for key in (
        "PUBLIC_REPOS",
        "GITHUB_TOKEN",
        "AI_REVIEW_PROVIDER",
        "AI_REVIEW_BASE_URL",
        "AI_REVIEW_MODEL",
        "AI_REVIEW_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    github_client.clear_cache()
    yield
    github_client.clear_cache()


def fixture_bundle() -> er.EvidenceBundle:
    raw: dict[str, object] = json.loads(FIXTURE.read_text())
    assessment = build_assessment(raw, "octocat", "Hello-World", "fixture", None)
    return er.build_evidence_bundle(assessment)


def canned_output(bundle: er.EvidenceBundle) -> dict[str, object]:
    by_id = {r.id: r for r in bundle.records}
    cited = ["E1", "E2", "E3", "E9"]
    return {
        "sections": {
            "evidence_summary": [
                {
                    "text": "Repository octocat/Hello-World shows 3 recent commits [E1] [E3].",
                    "citation_ids": ["E1", "E3"],
                }
            ],
            "deterministic_assessment_explanation": [
                {
                    "text": "The deterministic result is elevated change risk [E2] [E9].",
                    "citation_ids": ["E2", "E9"],
                }
            ],
            "evidence_gaps": [
                {
                    "text": "No public evidence was available for health status [E9].",
                    "citation_ids": ["E9"],
                }
            ],
            "human_review_checks": [
                {
                    "text": "Confirm CI status in the organization's internal system.",
                    "citation_ids": [],
                }
            ],
        },
        "sources": [
            {"id": cid, "label": by_id[cid].label, "url": by_id[cid].url, "kind": by_id[cid].kind}
            for cid in cited
        ],
    }


class FakeProvider(EvidenceReviewProvider):
    name = "fake"

    def __init__(self, output: dict[str, object] | None = None):
        self.output = output
        self.calls = 0

    def is_configured(self) -> bool:
        return True

    def generate(self, bundle: er.EvidenceBundle, system: str, user: str) -> dict[str, object]:
        self.calls += 1
        assert self.output is not None
        return self.output


def use_fake(monkeypatch, provider: EvidenceReviewProvider) -> None:
    monkeypatch.setattr(api_review, "get_review_provider", lambda: provider)


def test_unavailable_when_no_provider_and_never_calls_provider(monkeypatch):
    def boom(self, bundle, system, user):
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(api_review.NoProvider, "generate", boom)
    r = client.post(REVIEW_URL + "?fixture=true", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "unavailable"
    assert body["provider_configured"] is False
    assert "not configured" in (body["message"] or "").lower()
    assert body["sections"] is None
    assert body["deterministic_assessment"]["public_recommendation"] == (
        "ELEVATED CHANGE RISK — INVESTIGATE"
    )
    assert body["assessment_identity"]["candidate"] == "v1-0"


def test_reject_extra_request_fields():
    r = client.post(REVIEW_URL + "?fixture=true", json={"regenerate": False, "prompt": "hi"})
    assert r.status_code == 422


def test_unknown_repo_404():
    r = client.post(
        "/v1/public-data/assessments/someone/else/v1/evidence-review?fixture=true", json={}
    )
    assert r.status_code == 404


def test_unknown_candidate_404():
    r = client.post(
        "/v1/public-data/assessments/octocat/Hello-World/nope-9/evidence-review?fixture=true",
        json={},
    )
    assert r.status_code == 404


def test_available_with_fake_provider(monkeypatch):
    bundle = fixture_bundle()
    fake = FakeProvider(canned_output(bundle))
    use_fake(monkeypatch, fake)
    r = client.post(REVIEW_URL + "?fixture=true", json={"regenerate": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "available"
    assert body["provider_configured"] is True
    assert set(body["sections"].keys()) == {
        "evidence_summary",
        "deterministic_assessment_explanation",
        "evidence_gaps",
        "human_review_checks",
    }
    assert body["deterministic_assessment"]["deployment_readiness"] == (
        "not_assessable_from_public_data"
    )
    for source in body["sources"]:
        assert source["url"].startswith("https://github.com/")
    assert "AI output is explanatory assistance" in body["limitations"][-1]
    assert fake.calls == 1


def test_blocked_on_ungrounded_output(monkeypatch):
    bundle = fixture_bundle()
    bad = canned_output(bundle)
    assert isinstance(bad["sections"], dict)
    bad["sections"]["evidence_summary"] = [
        {"text": "You may proceed after review [E1].", "citation_ids": ["E1"]}
    ]
    fake = FakeProvider(bad)
    use_fake(monkeypatch, fake)
    r = client.post(REVIEW_URL + "?fixture=true", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "blocked"
    assert body["sections"] is None
    assert "grounding" in (body["message"] or "").lower()
    assert "proceed after review" not in r.text


def test_provider_error_maps_to_safe_502(monkeypatch):
    from api.evidence_review import ProviderError

    class BoomProvider(EvidenceReviewProvider):
        name = "boom"

        def is_configured(self) -> bool:
            return True

        def generate(self, bundle, system, user):
            raise ProviderError("timeout")

    use_fake(monkeypatch, BoomProvider())
    r = client.post(REVIEW_URL + "?fixture=true", json={})
    assert r.status_code == 502
    lowered = r.text.lower()
    assert "bearer" not in lowered
    assert "traceback" not in lowered
    assert "deterministic assessment" in r.text or "provider" in lowered


def test_rate_limit_maps_to_429(monkeypatch):
    from api.github_client import PublicDataNotFound, PublicDataRateLimited

    def fake_fetch(owner, repo):
        raise PublicDataRateLimited("github rate limit exceeded", reset_at="123")

    def fake_fixture(owner, repo):
        raise PublicDataNotFound("no saved fixture")

    monkeypatch.setattr(github_client, "fetch_live_evidence", fake_fetch)
    monkeypatch.setattr(github_client, "load_fixture_evidence", fake_fixture)
    r = client.post(REVIEW_URL + "?refresh=true", json={})
    assert r.status_code == 429


def test_stale_cache_fallback(monkeypatch):
    raw: dict[str, object] = json.loads(FIXTURE.read_text())
    assessment = build_assessment(raw, "octocat", "Hello-World", "live", None)
    key = "octocat/Hello-World|v1-0"
    github_client._cache[key] = (
        datetime.now(UTC) - timedelta(seconds=github_client.CACHE_TTL_SECONDS + 60),
        assessment,
    )

    def fake_fetch(owner, repo):
        raise github_client.PublicDataUnavailable("boom")

    monkeypatch.setattr(github_client, "fetch_live_evidence", fake_fetch)
    r = client.post(REVIEW_URL + "?refresh=true", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "unavailable"
    assert body["assessment_identity"]["served_from"] == "stale_cache"


def test_no_analyze_log_or_mapping_call(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("must not call scoring engine")

    monkeypatch.setattr("hollow_green.analyze.analyze_log", boom)
    monkeypatch.setattr("hollow_green.public_data.map_evidence_to_release_log", boom)
    bundle = fixture_bundle()
    use_fake(monkeypatch, FakeProvider(canned_output(bundle)))
    r = client.post(REVIEW_URL + "?fixture=true", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "available"


BANNED_REVIEW_TOKENS = [
    "PROCEED",
    "ROLLBACK VERIFIED",
    "HOLD / INVESTIGATE",
    "clean_success",
    "release approval",
    "deployment approval",
    "safe to deploy",
]


def test_review_response_has_no_approval_wording(monkeypatch):
    bundle = fixture_bundle()
    use_fake(monkeypatch, FakeProvider(canned_output(bundle)))
    r = client.post(REVIEW_URL + "?fixture=true", json={})
    assert r.status_code == 200
    for token in BANNED_REVIEW_TOKENS:
        assert token not in r.text, token


def test_no_real_http_or_provider(monkeypatch):
    import httpx

    def boom(*args, **kwargs):
        raise AssertionError("no live calls in tests")

    monkeypatch.setattr(httpx, "get", boom)
    monkeypatch.setattr(httpx, "post", boom)
    r = client.post(REVIEW_URL + "?fixture=true", json={})
    assert r.status_code == 200
    assert r.json()["status"] == "unavailable"


def test_test_provider_ignored_without_e2e_env():
    r = client.post(REVIEW_URL + "?fixture=true&test_provider=available", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "unavailable"


def test_test_provider_available_with_e2e_env(monkeypatch):
    monkeypatch.setenv("E2E_TEST_MODE", "1")
    r = client.post(REVIEW_URL + "?fixture=true&test_provider=available", json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "available"
    assert body["provider_configured"] is True


def test_test_provider_blocked_with_e2e_env(monkeypatch):
    monkeypatch.setenv("E2E_TEST_MODE", "1")
    r = client.post(REVIEW_URL + "?fixture=true&test_provider=blocked", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "blocked"


def test_test_provider_error_with_e2e_env(monkeypatch):
    monkeypatch.setenv("E2E_TEST_MODE", "1")
    r = client.post(REVIEW_URL + "?fixture=true&test_provider=error", json={})
    assert r.status_code == 502


def test_test_provider_bad_value_422_with_e2e_env(monkeypatch):
    monkeypatch.setenv("E2E_TEST_MODE", "1")
    r = client.post(REVIEW_URL + "?fixture=true&test_provider=evil", json={})
    assert r.status_code == 422


def test_fixture_only_env_serves_fixture(monkeypatch):
    def boom(owner, repo):
        raise AssertionError("must not call GitHub in fixture-only mode")

    monkeypatch.setattr(github_client, "fetch_live_evidence", boom)
    monkeypatch.setenv("PUBLIC_DATA_FIXTURE_ONLY", "1")
    r = client.get("/v1/public-repos/octocat/Hello-World/assessment")
    assert r.status_code == 200, r.text
    assert r.json()["served_from"] == "fixture"
