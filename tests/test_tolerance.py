"""Tolerance levels, survival flag, rollback visibility."""

from conftest import analyze_fixture


def test_high_tolerance_clean():
    r = analyze_fixture("synthetic_clean_001.json")
    assert r.tolerance.level == "high"
    assert r.tolerance.can_survive_second_failure is True


def test_critical_tolerance_failed_and_fragile():
    assert analyze_fixture("synthetic_failed_006.json").tolerance.level == "critical"
    assert (
        analyze_fixture("synthetic_failed_006.json").tolerance.can_survive_second_failure is False
    )
    assert analyze_fixture("synthetic_fragile_003.json").tolerance.level == "critical"


def test_low_tolerance_norollback_and_restart():
    assert analyze_fixture("synthetic_norollback_007.json").tolerance.level == "low"
    assert analyze_fixture("synthetic_restart_008.json").tolerance.level == "low"


def test_rollback_line_in_rationale():
    r = analyze_fixture("synthetic_rollback_005.json")
    assert any("rollback executed" in line for line in r.tolerance.rationale)
    assert any("verified" in line for line in r.tolerance.rationale)
    u = analyze_fixture("synthetic_rollback_unverified_005b.json")
    assert any("unverified" in line for line in u.tolerance.rationale)


def test_no_rollback_line_when_not_executed():
    r = analyze_fixture("synthetic_clean_001.json")
    assert all("rollback executed" not in line for line in r.tolerance.rationale)
