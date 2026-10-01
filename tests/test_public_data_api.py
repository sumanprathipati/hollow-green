"""Public-data API tests with mocked HTTP. Never calls GitHub."""

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient

from api import github_client
from api.github_client import PublicDataRateLimited
from api.main import create_app

client = TestClient(create_app())
FIXTURE = Path(__file__).parent / "fixtures" / "github" / "octocat__Hello-World.json"


@pytest.fixture(autouse=True)
def clean_env_cache(monkeypatch):
    monkeypatch.delenv("PUBLIC_REPOS", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    github_client.clear_cache()
    yield
    github_client.clear_cache()


def test_list_public_repos_default():
    r = client.get("/v1/public-repos")
    assert r.status_code == 200
    body = r.json()
    assert body == [
        {
            "repo_full_name": "octocat/Hello-World",
            "display_name": "octocat/Hello-World",
            "repo_url": "https://github.com/octocat/Hello-World",
        }
    ]


def test_unknown_repo_404():
    r = client.get("/v1/public-repos/someone/else/assessment")
    assert r.status_code == 404


def test_assessment_fixture_mode():
    r = client.get("/v1/public-repos/octocat/Hello-World/assessment?fixture=true")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["data_source"] == "public-github"
    assert body["served_from"] == "fixture"
    assert body["repo_full_name"] == "octocat/Hello-World"
    assert body["candidate"]["candidate_id"] == "v1-0"
    assert "Public repository evidence only" in body["disclaimer"]
    assert any("deployment readiness cannot be determined" in lim for lim in body["limitations"])
    assert "health" in body["unavailable_signals"]
    result = body["public_result"]
    assert result["change_risk_level"] == "elevated"
    assert result["evidence_completeness"] == "sufficient"
    assert result["deployment_readiness"] == "not_assessable_from_public_data"
    assert result["public_recommendation"] == "ELEVATED CHANGE RISK — INVESTIGATE"
    assert body["evidence"]["repo_url"] == "https://github.com/octocat/Hello-World"
    assert "report" not in body
    assert "release_log" not in body
    assert "GITHUB_TOKEN" not in r.text
    assert "Bearer" not in r.text


BANNED_PUBLIC_TOKENS = [
    "PROCEED",
    "ROLLBACK VERIFIED",
    "HOLD / INVESTIGATE",
    "clean_success",
    "recovered_success",
    "fragile_success",
    '"failed"',
]


def test_public_response_has_no_deployment_approval_wording():
    r = client.get("/v1/public-repos/octocat/Hello-World/assessment?fixture=true")
    assert r.status_code == 200
    text = r.text
    for token in BANNED_PUBLIC_TOKENS:
        assert token not in text, token


def test_assessment_live_then_cached(monkeypatch):
    raw = json.loads(FIXTURE.read_text())
    calls = {"n": 0}

    def fake_fetch(owner, repo):
        calls["n"] += 1
        return raw

    monkeypatch.setattr(github_client, "fetch_live_evidence", fake_fetch)
    first = client.get("/v1/public-repos/octocat/Hello-World/assessment?refresh=true")
    assert first.status_code == 200
    assert first.json()["served_from"] == "live"
    second = client.get("/v1/public-repos/octocat/Hello-World/assessment")
    assert second.status_code == 200
    assert second.json()["served_from"] == "live"
    assert calls["n"] == 1


def test_rate_limited_429_without_cache_or_fixture(monkeypatch):
    def fake_fetch(owner, repo):
        raise PublicDataRateLimited("github rate limit exceeded", reset_at="123")

    def fake_fixture(owner, repo):
        from api.github_client import PublicDataNotFound

        raise PublicDataNotFound("no saved fixture")

    monkeypatch.setattr(github_client, "fetch_live_evidence", fake_fetch)
    monkeypatch.setattr(github_client, "load_fixture_evidence", fake_fixture)
    r = client.get("/v1/public-repos/octocat/Hello-World/assessment?refresh=true")
    assert r.status_code == 429
    assert "rate limit" in r.text.lower()


def test_unknown_candidate_404():
    r = client.get("/v1/public-repos/octocat/Hello-World/assessment?fixture=true&candidate=nope-9")
    assert r.status_code == 404


def test_no_real_http(monkeypatch):
    import httpx

    def boom(*args, **kwargs):
        raise AssertionError("must not call GitHub in tests")

    monkeypatch.setattr(httpx, "get", boom)
    r = client.get("/v1/public-repos/octocat/Hello-World/assessment?fixture=true")
    assert r.status_code == 200
