"""Scoring: every rule has a match and a non-match. Reserve is the only score."""

from conftest import analyze_fixture, make_event, make_log

from hollow_green.analyze import analyze_log
from hollow_green.schemas import ReleaseLog
from hollow_green.scoring import recovery_load_for

T0 = "2026-01-01T00:00:00+00:00"
T1 = "2026-01-01T00:10:00+00:00"
T2 = "2026-01-01T00:20:00+00:00"


def rules_of(report):
    return {d.rule_id: d for d in report.score.deductions}


def test_retry_first_discount_match():
    report = analyze_fixture("synthetic_stale_010.json")
    assert rules_of(report)["retry.consume"].points == 6


def test_retry_no_retry_non_match():
    report = analyze_fixture("synthetic_clean_001.json")
    assert "retry.consume" not in rules_of(report)


def test_retry_repeat_tiering_and_cap_traceability():
    report = analyze_fixture("synthetic_fragile_003.json")
    d = rules_of(report)["retry.consume"]
    assert d.points == 42
    assert d.event_ids == ["evt-02", "evt-03", "evt-04", "evt-05"]


def test_retry_cap_lists_every_id():
    events = [make_event("e1", "rel-cap", T0, "deploy_started")]
    for i in range(8):
        events.append(
            make_event(
                f"r{i}",
                "rel-cap",
                f"2026-01-01T00:{i + 1:02d}:00+00:00",
                "retry_attempt",
                "system",
                {"attempt_no": i + 1},
            )
        )
    events.append(make_event("e9", "rel-cap", T2, "deploy_succeeded", "pipeline"))
    report = analyze_log(ReleaseLog.model_validate(make_log("rel-cap", events)))
    d = rules_of(report)["retry.consume"]
    assert d.points == 60
    assert len(d.event_ids) == 8


def test_retry_no_discount_when_failed():
    report = analyze_fixture("synthetic_failed_006.json")
    assert rules_of(report)["retry.consume"].points == 24


def test_human_only_retry_gets_no_discount():
    events = [
        make_event("e1", "rel-h", T0, "deploy_started"),
        make_event("r1", "rel-h", T1, "retry_attempt", "human", {"attempt_no": 1}),
        make_event("e9", "rel-h", T2, "deploy_succeeded", "pipeline"),
    ]
    report = analyze_log(ReleaseLog.model_validate(make_log("rel-h", events)))
    assert rules_of(report)["retry.consume"].points == 12


def test_budget_exhausted_match():
    report = analyze_fixture("synthetic_failed_006.json")
    assert rules_of(report)["retry.budget_exhausted"].points == 15


def test_budget_exhausted_non_match():
    report = analyze_fixture("synthetic_recovered_002.json")
    assert "retry.budget_exhausted" not in rules_of(report)


def test_restart_match_and_non_match():
    assert rules_of(analyze_fixture("synthetic_restart_008.json"))["restart.consume"].points == 30
    assert "restart.consume" not in rules_of(analyze_fixture("synthetic_clean_001.json"))


def test_manual_match_and_non_match():
    assert rules_of(analyze_fixture("synthetic_fragile_003.json"))["manual.consume"].points == 20
    assert "manual.consume" not in rules_of(analyze_fixture("synthetic_clean_001.json"))


def test_bypass_match_and_non_match():
    assert rules_of(analyze_fixture("synthetic_bypass_004.json"))["bypass.consume"].points == 25
    assert "bypass.consume" not in rules_of(analyze_fixture("synthetic_clean_001.json"))


def test_rollback_missing_match_and_non_match():
    assert (
        rules_of(analyze_fixture("synthetic_norollback_007.json"))["rollback.missing"].points == 25
    )
    assert "rollback.missing" not in rules_of(analyze_fixture("synthetic_clean_001.json"))


def test_rollback_stale_match_and_non_match():
    assert rules_of(analyze_fixture("synthetic_stale_010.json"))["rollback.stale"].points == 10
    assert "rollback.stale" not in rules_of(analyze_fixture("synthetic_clean_001.json"))


def test_no_points_for_clean_rollback_completed():
    report = analyze_fixture("synthetic_rollback_005.json")
    assert report.score.reserve_level == 100
    assert [d.rule_id for d in report.score.deductions] == []


def test_health_degraded_match_and_non_match():
    assert (
        rules_of(analyze_fixture("synthetic_restart_008.json"))["health.degraded_end"].points == 20
    )
    assert "health.degraded_end" not in rules_of(analyze_fixture("synthetic_clean_001.json"))


def test_health_failed_match_and_non_match():
    assert rules_of(analyze_fixture("synthetic_failed_006.json"))["health.failed_end"].points == 40
    assert "health.failed_end" not in rules_of(analyze_fixture("synthetic_clean_001.json"))


def test_time_low_match_and_non_match():
    assert rules_of(analyze_fixture("synthetic_fragile_003.json"))["time.low"].points == 15
    assert "time.low" not in rules_of(analyze_fixture("synthetic_clean_001.json"))


def test_time_critical_match_and_non_match():
    report = analyze_fixture("synthetic_window_009.json")
    assert rules_of(report)["time.low"].points == 15
    assert rules_of(report)["time.critical"].points == 10
    assert "time.critical" not in rules_of(analyze_fixture("synthetic_fragile_003.json"))


def test_fragile_003_exact_reserve_and_load():
    report = analyze_fixture("synthetic_fragile_003.json")
    assert report.score.reserve_level == 23
    assert report.score.recovery_load == "critical"


def test_recovery_load_mapping():
    assert recovery_load_for(100) == "low"
    assert recovery_load_for(82) == "low"
    assert recovery_load_for(79) == "medium"
    assert recovery_load_for(50) == "medium"
    assert recovery_load_for(49) == "high"
    assert recovery_load_for(25) == "high"
    assert recovery_load_for(24) == "critical"
    assert recovery_load_for(0) == "critical"


def test_every_deduction_has_event_ids():
    for name in [
        "synthetic_recovered_002.json",
        "synthetic_fragile_003.json",
        "synthetic_failed_006.json",
        "synthetic_window_009.json",
    ]:
        report = analyze_fixture(name)
        for d in report.score.deductions:
            assert len(d.event_ids) >= 1
            assert d.points > 0
