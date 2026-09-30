"""Shared test helpers."""

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from hollow_green.analyze import analyze_log  # noqa: E402
from hollow_green.schemas import ReleaseLog  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def load_payload(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def analyze_fixture(name: str):  # -> ReleaseReport
    payload = load_payload(name)
    log = ReleaseLog.model_validate(payload)
    return analyze_log(log)


def make_event(
    event_id: str,
    release_id: str,
    ts: str,
    type: str,
    actor: str = "system",
    details: dict | None = None,
) -> dict:
    return {
        "event_id": event_id,
        "release_id": release_id,
        "ts": ts,
        "type": type,
        "actor": actor,
        "details": details or {},
    }


def make_log(
    release_id: str = "rel-test",
    events: list[dict] | None = None,
    window_minutes: int = 60,
    retry_budget_max: int = 5,
) -> dict:
    return {
        "schema_version": "1.0",
        "release_id": release_id,
        "service": "checkout-api-synth",
        "window_minutes": window_minutes,
        "retry_budget_max": retry_budget_max,
        "events": events or [],
    }
