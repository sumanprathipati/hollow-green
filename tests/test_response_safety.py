"""Public responses must not expose flags, tokens, prompts, or internals."""

import sys

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient

from api import evidence_review as api_review
from api import github_client
from api.evidence_review import EvidenceReviewProvider
from api.main import create_app

client = TestClient(create_app())

# AI variable *names* are public setup documentation (see README) and may
# appear in the unavailable guidance message. Values must never appear, which
# holds by construction since values are never placed in responses.
FORBIDDEN_FRAGMENTS = [
    "E2E_TEST_MODE",
    "FIXTURE_ONLY",
    "GITHUB_TOKEN",
    "Bearer",
    "test_provider",
    "Traceback",
    "/Users/",
    "src/api/",
    '.py"',
    "uvicorn",
    "pydantic",
    "httpx",
]


@pytest.fixture(autouse=True)
def clean_safety_env(monkeypatch):
    for key in (
        "PUBLIC_REPOS",
        "GITHUB_TOKEN",
        "AI_REVIEW_PROVIDER",
        "AI_REVIEW_BASE_URL",
        "AI_REVIEW_MODEL",
        "AI_REVIEW_API_KEY",
        "E2E_TEST_MODE",
        "PUBLIC_DATA_FIXTURE_ONLY",
    ):
        monkeypatch.delenv(key, raising=False)
    github_client.clear_cache()
    yield
    github_client.clear_cache()


def assert_no_forbidden(text: str) -> None:
    for fragment in FORBIDDEN_FRAGMENTS:
        assert fragment not in text, fragment


def test_health_exposes_only_safe_fields():
    body = client.get("/v1/health").json()
    assert set(body.keys()) == {"status", "environment", "public_data", "ai_review"}
    assert_no_forbidden(client.get("/v1/health").text)


def test_public_assessment_hides_internals():
    r = client.get("/v1/public-repos/octocat/Hello-World/assessment?fixture=true")
    assert r.status_code == 200
    assert_no_forbidden(r.text)


def test_review_unavailable_hides_internals():
    r = client.post(
        "/v1/public-data/assessments/octocat/Hello-World/v1-0/evidence-review?fixture=true",
        json={},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "unavailable"
    assert_no_forbidden(r.text)


def test_review_blocked_hides_rejected_output(monkeypatch):
    from hollow_green import evidence_review as er

    class BadProvider(EvidenceReviewProvider):
        name = "bad"

        def is_configured(self) -> bool:
            return True

        def generate(self, bundle: er.EvidenceBundle, system: str, user: str):
            return {
                "sections": {
                    "evidence_summary": [
                        {"text": "You may proceed now [E1].", "citation_ids": ["E1"]}
                    ],
                    "deterministic_assessment_explanation": [
                        {"text": "x [E1].", "citation_ids": ["E1"]}
                    ],
                    "evidence_gaps": [{"text": "y [E1].", "citation_ids": ["E1"]}],
                    "human_review_checks": [{"text": "Check CI.", "citation_ids": []}],
                },
                "sources": [
                    {
                        "id": "E1",
                        "label": "Repository: octocat/Hello-World",
                        "url": "https://github.com/octocat/Hello-World",
                        "kind": "repository",
                    }
                ],
            }

    monkeypatch.setattr(api_review, "get_review_provider", lambda: BadProvider())
    r = client.post(
        "/v1/public-data/assessments/octocat/Hello-World/v1-0/evidence-review?fixture=true",
        json={},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"
    assert "You may proceed now" not in r.text
    assert_no_forbidden(r.text)


def test_rate_limit_error_hides_internals(monkeypatch):
    from api.github_client import PublicDataUnavailable
    from api.rate_limit import reset_rate_limiters

    reset_rate_limiters()
    monkeypatch.setenv("PUBLIC_REPOS", "octocat/NoFixture")

    def fake_fetch(owner, repo):
        raise PublicDataUnavailable("upstream exploded")

    monkeypatch.setattr(github_client, "fetch_live_evidence", fake_fetch)
    r = client.get("/v1/public-repos/octocat/NoFixture/assessment?refresh=true")
    assert r.status_code == 502
    assert_no_forbidden(r.text)
