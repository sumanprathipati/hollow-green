"""API contract: health, version, analyze 200s and 422s, terminology regression."""

import sys

sys.path.insert(0, "src")

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app

client = TestClient(create_app())
FIXTURES = Path(__file__).parent / "fixtures"


def post_fixture(name: str):
    payload = json.loads((FIXTURES / name).read_text())
    return client.post("/v1/releases:analyze", json=payload)


def test_health():
    body = client.get("/v1/health").json()
    assert body["status"] == "ok"
    assert body == {
        "status": "ok",
        "environment": "development",
        "public_data": "available",
        "ai_review": "unavailable",
    }


def test_version():
    assert client.get("/v1/version").json() == {
        "schema_version": "1.0",
        "app": "hollow-green",
    }


def test_analyze_clean_200():
    r = post_fixture("synthetic_clean_001.json")
    assert r.status_code == 200
    body = r.json()
    assert body["classification"] == "clean_success"
    assert body["score"]["reserve_level"] == 100
    assert body["score"]["recovery_load"] == "low"


def test_analyze_fragile_003_exact():
    r = post_fixture("synthetic_fragile_003.json")
    assert r.status_code == 200
    body = r.json()
    assert body["score"]["reserve_level"] == 23
    assert body["score"]["recovery_load"] == "critical"
    assert body["classification"] == "fragile_success"


def test_analyze_all_fixtures_200():
    for name in [p.name for p in FIXTURES.glob("*.json")]:
        r = post_fixture(name)
        assert r.status_code == 200, name


def test_422_unknown_version():
    payload = json.loads((FIXTURES / "synthetic_clean_001.json").read_text())
    payload["schema_version"] = "2.0"
    assert client.post("/v1/releases:analyze", json=payload).status_code == 422


def test_422_duplicate_event_id_lists_ids():
    payload = json.loads((FIXTURES / "synthetic_clean_001.json").read_text())
    payload["events"].append(dict(payload["events"][0]))
    r = client.post("/v1/releases:analyze", json=payload)
    assert r.status_code == 422
    assert "duplicate_event_ids" in str(r.json())


def test_422_zero_terminal():
    payload = json.loads((FIXTURES / "synthetic_clean_001.json").read_text())
    payload["events"] = [e for e in payload["events"] if e["type"] != "deploy_succeeded"]
    assert client.post("/v1/releases:analyze", json=payload).status_code == 422


def test_422_multiple_terminals():
    payload = json.loads((FIXTURES / "synthetic_clean_001.json").read_text())
    extra = dict(payload["events"][-1])
    extra["event_id"] = "evt-99"
    extra["type"] = "deploy_failed"
    payload["events"].append(extra)
    assert client.post("/v1/releases:analyze", json=payload).status_code == 422


def test_422_bad_extension():
    payload = json.loads((FIXTURES / "synthetic_window_009.json").read_text())
    for e in payload["events"]:
        if e["type"] == "window_extended":
            e["details"]["extension_minutes"] = 0
    assert client.post("/v1/releases:analyze", json=payload).status_code == 422


def test_422_unknown_event_type():
    payload = json.loads((FIXTURES / "synthetic_clean_001.json").read_text())
    payload["events"][1]["type"] = "warp_drive"
    assert client.post("/v1/releases:analyze", json=payload).status_code == 422


def test_terminology_regression_no_old_keys():
    r = post_fixture("synthetic_recovered_002.json")
    text = r.text
    assert "debt_score" not in text
    assert "debt_id" not in text
    assert "repayment" not in text
    assert '"restored"' not in text
    body = r.json()
    assert "follow_ups" in body
    assert "reserve_level" in body["score"]
    assert "recovery_load" in body["score"]
    for fu in body["follow_ups"]:
        assert set(fu.keys()) == {
            "follow_up_id",
            "kind",
            "event_ids",
            "severity",
            "required_action",
            "status",
        }
