"""Ingest validation: uniqueness, terminal count, binding, time sanity."""

import pytest
from conftest import make_event, make_log

from hollow_green.analyze import analyze_log
from hollow_green.ingest import IngestError, validate_and_sort
from hollow_green.schemas import ReleaseLog

T0 = "2026-01-01T00:00:00+00:00"
T1 = "2026-01-01T00:10:00+00:00"
T2 = "2026-01-01T00:20:00+00:00"


def base_events(release="rel-test"):
    return [
        make_event("e1", release, T0, "deploy_started"),
        make_event("e2", release, T1, "health_report", "monitor", {"status": "pass"}),
        make_event("e3", release, T2, "deploy_succeeded", "pipeline"),
    ]


def test_valid_log_sorts_and_passes():
    log = ReleaseLog.model_validate(make_log(events=base_events()))
    ordered = validate_and_sort(log)
    assert [e.event_id for e in ordered] == ["e1", "e2", "e3"]


def test_duplicate_event_id_rejected_with_ids_listed():
    events = base_events()
    events.append(make_event("e2", "rel-test", T2, "deploy_progress", "pipeline"))
    log = ReleaseLog.model_validate(make_log(events=events))
    with pytest.raises(IngestError) as exc:
        validate_and_sort(log)
    assert exc.value.duplicate_event_ids == ["e2"]


def test_duplicate_event_id_not_silently_deduped():
    # non-match counterpart: unique ids pass
    log = ReleaseLog.model_validate(make_log(events=base_events()))
    assert len(validate_and_sort(log)) == 3


def test_zero_terminal_events_rejected():
    events = [
        make_event("e1", "rel-test", T0, "deploy_started"),
        make_event("e2", "rel-test", T1, "deploy_progress", "pipeline"),
    ]
    log = ReleaseLog.model_validate(make_log(events=events))
    with pytest.raises(IngestError, match="zero terminal"):
        validate_and_sort(log)


def test_exactly_one_terminal_accepted():
    log = ReleaseLog.model_validate(make_log(events=base_events()))
    report = analyze_log(log)
    assert report.terminal == "succeeded"


def test_multiple_terminal_events_rejected():
    events = base_events() + [
        make_event("e4", "rel-test", "2026-01-01T00:25:00+00:00", "deploy_failed")
    ]
    log = ReleaseLog.model_validate(make_log(events=events))
    with pytest.raises(IngestError, match="multiple terminal"):
        validate_and_sort(log)


def test_release_id_mismatch_rejected():
    events = base_events()
    events[1] = make_event("e2", "rel-other", T1, "health_report", "monitor", {"status": "pass"})
    log = ReleaseLog.model_validate(make_log(events=events))
    with pytest.raises(IngestError, match="release_id mismatch"):
        validate_and_sort(log)


def test_release_id_match_passes():
    log = ReleaseLog.model_validate(make_log(events=base_events()))
    assert validate_and_sort(log)


def test_missing_deploy_started_rejected():
    events = [
        make_event("e2", "rel-test", T1, "health_report", "monitor", {"status": "pass"}),
        make_event("e3", "rel-test", T2, "deploy_succeeded", "pipeline"),
    ]
    log = ReleaseLog.model_validate(make_log(events=events))
    with pytest.raises(IngestError, match="deploy_started"):
        validate_and_sort(log)


def test_negative_elapsed_rejected():
    events = [
        make_event("e1", "rel-test", T2, "deploy_started"),
        make_event("e3", "rel-test", T0, "deploy_succeeded", "pipeline"),
    ]
    log = ReleaseLog.model_validate(make_log(events=events))
    with pytest.raises(IngestError, match="negative elapsed"):
        validate_and_sort(log)


def test_bad_extension_minutes_rejected():
    events = [
        make_event("e1", "rel-test", T0, "deploy_started"),
        make_event("e2", "rel-test", T1, "window_extended", "pipeline", {"extension_minutes": 0}),
        make_event("e3", "rel-test", T2, "deploy_succeeded", "pipeline"),
    ]
    log = ReleaseLog.model_validate(make_log(events=events))
    with pytest.raises(IngestError, match="extension_minutes"):
        validate_and_sort(log)


def test_missing_extension_minutes_rejected():
    events = [
        make_event("e1", "rel-test", T0, "deploy_started"),
        make_event("e2", "rel-test", T1, "window_extended", "pipeline", {}),
        make_event("e3", "rel-test", T2, "deploy_succeeded", "pipeline"),
    ]
    log = ReleaseLog.model_validate(make_log(events=events))
    with pytest.raises(IngestError, match="extension_minutes"):
        validate_and_sort(log)


def test_unknown_event_type_rejected():
    events = base_events() + [make_event("e9", "rel-test", T2, "warp_drive", "system")]
    log = ReleaseLog.model_validate(make_log(events=events))
    with pytest.raises(IngestError, match="unknown event"):
        validate_and_sort(log)
