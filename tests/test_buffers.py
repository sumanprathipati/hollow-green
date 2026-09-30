"""Buffer snapshots and the exact original-window time formula."""

from conftest import analyze_fixture, make_event, make_log

from hollow_green.analyze import analyze_log
from hollow_green.schemas import ReleaseLog

T0 = "2026-01-01T00:00:00+00:00"


def test_clean_buffers_no_extension():
    report = analyze_fixture("synthetic_clean_001.json")
    b = report.score.buffers
    assert b.retries_used == 0
    assert b.retries_left == 5
    assert b.retry_reserve_pct == 100.0
    assert b.time_remaining_original_pct == 66.7
    assert b.extension_total_min == 0.0
    assert b.rollback_available is True
    assert b.rollback_fresh is True
    assert b.health_end == "pass"
    assert b.manual_count == 0


def test_one_extension_uses_original_not_effective():
    report = analyze_fixture("synthetic_window_009.json")
    b = report.score.buffers
    # elapsed 55 of original 60 -> 8.3% scored; effective 75 -> 26.7% display
    assert b.time_remaining_original_pct == 8.3
    assert b.time_remaining_effective_pct == 26.7
    assert b.extension_total_min == 15.0
    # scoring still deducts full 25 time points
    rules = {d.rule_id: d.points for d in report.score.deductions}
    assert rules.get("time.low") == 15
    assert rules.get("time.critical") == 10


def test_extension_never_raises_reserve():
    base = {
        "schema_version": "1.0",
        "release_id": "rel-x",
        "service": "checkout-api-synth",
        "window_minutes": 60,
        "retry_budget_max": 5,
        "events": [
            make_event("e1", "rel-x", "2026-01-01T00:00:00+00:00", "deploy_started"),
            make_event(
                "e2",
                "rel-x",
                "2026-01-01T00:50:00+00:00",
                "health_report",
                "monitor",
                {"status": "pass"},
            ),
            make_event("e3", "rel-x", "2026-01-01T00:55:00+00:00", "deploy_succeeded", "pipeline"),
        ],
    }
    ext = {
        "schema_version": "1.0",
        "release_id": "rel-x",
        "service": "checkout-api-synth",
        "window_minutes": 60,
        "retry_budget_max": 5,
        "events": [
            make_event("e1", "rel-x", "2026-01-01T00:00:00+00:00", "deploy_started"),
            make_event(
                "w1",
                "rel-x",
                "2026-01-01T00:30:00+00:00",
                "window_extended",
                "pipeline",
                {"extension_minutes": 60},
            ),
            make_event(
                "e2",
                "rel-x",
                "2026-01-01T00:50:00+00:00",
                "health_report",
                "monitor",
                {"status": "pass"},
            ),
            make_event("e3", "rel-x", "2026-01-01T00:55:00+00:00", "deploy_succeeded", "pipeline"),
        ],
    }
    r_base = analyze_log(ReleaseLog.model_validate(base))
    r_ext = analyze_log(ReleaseLog.model_validate(ext))
    assert r_ext.score.reserve_level <= r_base.score.reserve_level


def test_rollback_snapshot_defaults_available_fresh():
    report = analyze_fixture("synthetic_failed_006.json")
    # no snapshot signal -> defaults True/True
    assert report.score.buffers.rollback_available is True
    assert report.score.buffers.rollback_fresh is True


def test_rollback_unavailable_and_stale_signals():
    no_rb = analyze_fixture("synthetic_norollback_007.json")
    assert no_rb.score.buffers.rollback_available is False
    stale = analyze_fixture("synthetic_stale_010.json")
    assert stale.score.buffers.rollback_available is True
    assert stale.score.buffers.rollback_fresh is False


def test_health_unknown_when_no_report():
    payload = make_log(
        release_id="rel-h",
        events=[
            make_event("e1", "rel-h", "2026-01-01T00:00:00+00:00", "deploy_started"),
            make_event("e3", "rel-h", "2026-01-01T00:20:00+00:00", "deploy_succeeded", "pipeline"),
        ],
    )
    report = analyze_log(ReleaseLog.model_validate(payload))
    assert report.score.buffers.health_end == "unknown"
