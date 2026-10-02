"""CORS production/development rules. No live calls."""

import sys

sys.path.insert(0, "src")

import pytest
from fastapi.testclient import TestClient

from api import settings
from api.main import create_app

PROD_ORIGIN = "https://hollow-green.example"
EVIL_ORIGIN = "http://evil.test"


@pytest.fixture(autouse=True)
def clean_cors_env(monkeypatch):
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    yield


def make_client() -> TestClient:
    return TestClient(create_app())


def test_dev_origin_allowed_by_default():
    client = make_client()
    r = client.get("/v1/demo-releases", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_configured_production_origin_allowed(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", PROD_ORIGIN)
    client = make_client()
    r = client.get("/v1/demo-releases", headers={"Origin": PROD_ORIGIN})
    assert r.headers.get("access-control-allow-origin") == PROD_ORIGIN


def test_disallowed_origin_gets_no_echo():
    client = make_client()
    r = client.get("/v1/demo-releases", headers={"Origin": EVIL_ORIGIN})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") is None


def test_preflight_allows_required_get_post(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", PROD_ORIGIN)
    client = make_client()
    for method in ("GET", "POST"):
        r = client.options(
            "/v1/releases:analyze",
            headers={
                "Origin": PROD_ORIGIN,
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert r.status_code == 200, method
        allow_methods = r.headers.get("access-control-allow-methods", "")
        assert "GET" in allow_methods
        assert "POST" in allow_methods


def test_no_credentials_and_no_wildcard(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", PROD_ORIGIN)
    client = make_client()
    r = client.get("/v1/demo-releases", headers={"Origin": PROD_ORIGIN})
    assert r.headers.get("access-control-allow-credentials") is None
    assert r.headers.get("access-control-allow-origin") == PROD_ORIGIN
    assert settings.allowed_origins() == [
        PROD_ORIGIN,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    with pytest.raises(ValueError):
        settings.parse_allowed_origins("*")
