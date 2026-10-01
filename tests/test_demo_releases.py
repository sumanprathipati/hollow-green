"""Demo fixture endpoints + CORS contract."""

import sys

sys.path.insert(0, "src")

from fastapi.testclient import TestClient

from api.main import create_app

client = TestClient(create_app())

ALLOWED = ["http://localhost:3000", "http://127.0.0.1:3000"]
DISALLOWED = "http://evil.test"


def test_demo_list_shape():
    r = client.get("/v1/demo-releases")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert len(body) == 5
    ids = {item["release_id"] for item in body}
    assert ids == {
        "rel-clean-001",
        "rel-recovered-002",
        "rel-fragile-003",
        "rel-rollback-005",
        "rel-failed-006",
    }
    for item in body:
        assert set(item.keys()) == {"release_id", "display_name", "classification_hint"}
    hints = {item["release_id"]: item["classification_hint"] for item in body}
    assert hints == {
        "rel-clean-001": "clean_success",
        "rel-recovered-002": "recovered_success",
        "rel-fragile-003": "fragile_success",
        "rel-rollback-005": "rollback",
        "rel-failed-006": "failed",
    }


def test_demo_get_each_known():
    for release_id in [
        "rel-clean-001",
        "rel-recovered-002",
        "rel-fragile-003",
        "rel-rollback-005",
        "rel-failed-006",
    ]:
        r = client.get(f"/v1/demo-releases/{release_id}")
        assert r.status_code == 200, release_id
        body = r.json()
        assert body["release_id"] == release_id
        assert body["schema_version"] == "1.0"
        assert isinstance(body["events"], list)


def test_demo_get_unknown_404_no_path_leak():
    r = client.get("/v1/demo-releases/rel-unknown-999")
    assert r.status_code == 404
    assert r.json() == {"detail": "unknown demo release"}
    assert ".json" not in r.text
    assert "fixtures" not in r.text


def test_demo_get_traversal_404():
    for bad in [
        "..",
        "%2e%2e",
        "synthetic_clean_001.json",
        "/etc/passwd",
        "tests/fixtures/synthetic_clean_001.json",
    ]:
        r = client.get(f"/v1/demo-releases/{bad}")
        assert r.status_code == 404, bad
        assert ".json" not in r.text or "unknown demo release" in r.text
        assert "fixtures" not in r.text
        assert "/etc/passwd" not in r.text


def test_cors_both_allowed_origins():
    for origin in ALLOWED:
        r = client.options(
            "/v1/demo-releases",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200, origin
        assert r.headers.get("access-control-allow-origin") == origin


def test_cors_get_echoes_allowed_origin():
    for origin in ALLOWED:
        r = client.get("/v1/demo-releases", headers={"Origin": origin})
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == origin


def test_cors_disallowed_origin_no_echo():
    r = client.options(
        "/v1/demo-releases",
        headers={
            "Origin": DISALLOWED,
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette returns no ACAO header for disallowed origins on preflight;
    # the key assertion is it never echoes "*" and never echoes the evil origin.
    assert r.headers.get("access-control-allow-origin") != "*"
    assert r.headers.get("access-control-allow-origin") != DISALLOWED
    r2 = client.get("/v1/demo-releases", headers={"Origin": DISALLOWED})
    assert r2.status_code == 200
    assert r2.headers.get("access-control-allow-origin") != "*"
    assert r2.headers.get("access-control-allow-origin") != DISALLOWED


def test_cors_no_wildcard_anywhere():
    r = client.get("/v1/demo-releases", headers={"Origin": ALLOWED[0]})
    assert r.headers.get("access-control-allow-origin") != "*"


def test_demo_fragile_003_still_scores_23_critical():
    r = client.get("/v1/demo-releases/rel-fragile-003")
    assert r.status_code == 200
    payload = r.json()
    a = client.post("/v1/releases:analyze", json=payload)
    assert a.status_code == 200
    body = a.json()
    assert body["score"]["reserve_level"] == 23
    assert body["score"]["recovery_load"] == "critical"
    assert body["classification"] == "fragile_success"
