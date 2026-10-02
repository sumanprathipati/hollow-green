"""Rate-limit behavior: deterministic clock unit tests + route integration."""

import sys

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient

from api import github_client, rate_limit
from api.main import create_app
from api.rate_limit import RateLimiter, reset_rate_limiters

client = TestClient(create_app())


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture(autouse=True)
def clean_rate_env(monkeypatch):
    monkeypatch.delenv("PUBLIC_REPOS", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("TRUST_PROXY_HEADERS", raising=False)
    reset_rate_limiters()
    github_client.clear_cache()
    yield
    reset_rate_limiters()
    github_client.clear_cache()


def test_under_limit_allows_all():
    clock = FakeClock()
    limiter = RateLimiter(3, 60, clock=clock)
    for _ in range(3):
        allowed, _ = limiter.check("ip")
        assert allowed


def test_over_limit_rejects_with_retry_after():
    clock = FakeClock()
    limiter = RateLimiter(2, 60, clock=clock)
    assert limiter.check("ip")[0]
    assert limiter.check("ip")[0]
    allowed, retry_after = limiter.check("ip")
    assert not allowed
    assert 0 < retry_after <= 60


def test_window_reset_allows_again():
    clock = FakeClock()
    limiter = RateLimiter(1, 60, clock=clock)
    assert limiter.check("ip")[0]
    assert not limiter.check("ip")[0]
    clock.advance(61)
    assert limiter.check("ip")[0]


def test_limits_are_independent_per_route_and_key():
    clock = FakeClock()
    first = RateLimiter(1, 60, clock=clock)
    second = RateLimiter(1, 60, clock=clock)
    assert first.check("a")[0]
    assert not first.check("a")[0]
    assert first.check("b")[0]
    assert second.check("a")[0]


def test_client_ip_prefers_direct_connection():
    from fastapi import Request

    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"9.9.9.9")],
        "client": ("1.2.3.4", 5000),
    }
    request = Request(scope)
    assert rate_limit.client_ip(request) == "1.2.3.4"


def test_client_ip_honors_proxy_only_when_trusted(monkeypatch):
    from fastapi import Request

    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"9.9.9.9, 8.8.8.8")],
        "client": ("1.2.3.4", 5000),
    }
    assert rate_limit.client_ip(Request(scope)) == "1.2.3.4"
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "1")
    assert rate_limit.client_ip(Request(scope)) == "9.9.9.9"


def live_raw():
    import json
    from pathlib import Path

    return json.loads(
        (Path(__file__).parent / "fixtures" / "github" / "octocat__Hello-World.json").read_text()
    )


def test_assessment_live_path_limited_with_retry_after(monkeypatch):
    monkeypatch.setattr(github_client, "fetch_live_evidence", lambda o, r: live_raw())
    url = "/v1/public-repos/octocat/Hello-World/assessment?refresh=true"
    for _ in range(10):
        r = client.get(url)
        assert r.status_code == 200, r.text
    r = client.get(url)
    assert r.status_code == 429
    assert r.headers.get("Retry-After") is not None
    assert int(r.headers["Retry-After"]) >= 1
    assert "rate limit exceeded" in r.json()["detail"]


def test_cached_reads_do_not_consume_allowance(monkeypatch):
    monkeypatch.setattr(github_client, "fetch_live_evidence", lambda o, r: live_raw())
    assert (
        client.get("/v1/public-repos/octocat/Hello-World/assessment?refresh=true").status_code
        == 200
    )
    for _ in range(15):
        r = client.get("/v1/public-repos/octocat/Hello-World/assessment")
        assert r.status_code == 200, r.text


def test_review_route_has_own_smaller_allowance(monkeypatch):
    monkeypatch.setattr(github_client, "fetch_live_evidence", lambda o, r: live_raw())
    url = "/v1/public-data/assessments/octocat/Hello-World/v1-0/evidence-review?refresh=true"
    for _ in range(5):
        r = client.post(url, json={})
        assert r.status_code == 200, r.text
    r = client.post(url, json={})
    assert r.status_code == 429
    assert r.headers.get("Retry-After") is not None
    body = r.text.lower()
    assert "bearer" not in body
    assert "traceback" not in body
    assert "ai_review_api_key" not in body
