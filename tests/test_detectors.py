"""Detectors map each recovery action and signal."""

from conftest import analyze_fixture, make_event, make_log

from hollow_green import detectors
from hollow_green.ingest import validate_and_sort
from hollow_green.schemas import ReleaseLog


def ordered(events):
    log = ReleaseLog.model_validate(make_log(events=events))
    return validate_and_sort(log)


T0 = "2026-01-01T00:00:00+00:00"
T1 = "2026-01-01T00:10:00+00:00"
T2 = "2026-01-01T00:20:00+00:00"


def test_detects_each_recovery_action():
    ev = [
        make_event("e1", "rel-test", T0, "deploy_started"),
        make_event("r1", "rel-test", T1, "retry_attempt", "system", {"attempt_no": 1}),
        make_event("s1", "rel-test", T1, "service_restart"),
        make_event("m1", "rel-test", T1, "manual_override", "human"),
        make_event("b1", "rel-test", T1, "bypass", "pipeline", {"bypass_kind": "approval_skip"}),
        make_event("w1", "rel-test", T1, "window_extended", "pipeline", {"extension_minutes": 5}),
        make_event("rb1", "rel-test", T1, "rollback_started"),
        make_event("rb2", "rel-test", T1, "rollback_completed"),
        make_event("e9", "rel-test", T2, "deploy_succeeded", "pipeline"),
    ]
    o = ordered(ev)
    assert len(detectors.retries(o)) == 1
    assert len(detectors.restarts(o)) == 1
    assert len(detectors.manual_overrides(o)) == 1
    assert len(detectors.bypasses(o)) == 1
    assert len(detectors.extensions(o)) == 1
    assert len(detectors.rollback_events(o)) == 2
    assert detectors.has_recovery_action(o) is True


def test_no_recovery_action_on_clean():
    report = analyze_fixture("synthetic_clean_001.json")
    assert report.follow_ups == []
    assert report.score.reserve_level == 100


def test_automated_vs_human_retry_split():
    ev = [
        make_event("e1", "rel-test", T0, "deploy_started"),
        make_event("r1", "rel-test", T1, "retry_attempt", "system", {"attempt_no": 1}),
        make_event("r2", "rel-test", T1, "retry_attempt", "human", {"attempt_no": 2}),
        make_event("e9", "rel-test", T2, "deploy_succeeded", "pipeline"),
    ]
    o = ordered(ev)
    assert len(detectors.retries(o)) == 2
    assert len(detectors.automated_retries(o)) == 1


def test_extension_total_sums():
    ev = [
        make_event("e1", "rel-test", T0, "deploy_started"),
        make_event("w1", "rel-test", T1, "window_extended", "pipeline", {"extension_minutes": 5}),
        make_event("w2", "rel-test", T1, "window_extended", "pipeline", {"extension_minutes": 7}),
        make_event("e9", "rel-test", T2, "deploy_succeeded", "pipeline"),
    ]
    o = ordered(ev)
    assert detectors.extension_total_min(o) == 12.0
