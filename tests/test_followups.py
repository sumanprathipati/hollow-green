"""RecoveryFollowUp shape and conditional creation."""

from conftest import analyze_fixture


def test_follow_up_shape_and_open_status():
    report = analyze_fixture("synthetic_recovered_002.json")
    assert len(report.follow_ups) == 2
    for fu in report.follow_ups:
        assert fu.follow_up_id
        assert fu.kind
        assert len(fu.event_ids) >= 1
        assert fu.severity in ("low", "medium", "high", "critical")
        assert fu.required_action
        assert fu.status == "open"


def test_retry_follow_up_severities_first_low_then_medium():
    report = analyze_fixture("synthetic_recovered_002.json")
    by_event = {fu.event_ids[0]: fu for fu in report.follow_ups}
    assert by_event["evt-02"].severity == "low"
    assert by_event["evt-04"].severity == "medium"


def test_clean_has_no_follow_ups():
    assert analyze_fixture("synthetic_clean_001.json").follow_ups == []


def test_restart_follow_ups():
    report = analyze_fixture("synthetic_restart_008.json")
    restarts = [fu for fu in report.follow_ups if fu.kind == "restart"]
    assert len(restarts) == 2
    assert all(fu.severity == "medium" for fu in restarts)


def test_manual_follow_up():
    report = analyze_fixture("synthetic_fragile_003.json")
    manuals = [fu for fu in report.follow_ups if fu.kind == "manual_override"]
    assert len(manuals) == 1
    assert manuals[0].severity == "high"
    assert "runbook" in manuals[0].required_action


def test_bypass_health_skip_is_critical():
    report = analyze_fixture("synthetic_bypass_004.json")
    bypasses = [fu for fu in report.follow_ups if fu.kind == "bypass"]
    assert len(bypasses) == 1
    assert bypasses[0].severity == "critical"


def test_clean_rollback_has_no_rollback_follow_up():
    report = analyze_fixture("synthetic_rollback_005.json")
    assert [fu for fu in report.follow_ups if fu.kind == "rollback"] == []
    assert report.rollback_summary.verified is True


def test_unverified_rollback_has_follow_up():
    report = analyze_fixture("synthetic_rollback_unverified_005b.json")
    rbs = [fu for fu in report.follow_ups if fu.kind == "rollback"]
    assert len(rbs) == 1
    assert "health check" in rbs[0].required_action
    assert rbs[0].status == "open"


def test_window_extension_follow_up():
    report = analyze_fixture("synthetic_window_009.json")
    exts = [fu for fu in report.follow_ups if fu.kind == "window_extension"]
    assert len(exts) == 1
    assert exts[0].severity == "high"  # 15/60 = 25% > 20%
    assert "15m" in exts[0].required_action


def test_no_extension_no_extension_follow_up():
    report = analyze_fixture("synthetic_clean_001.json")
    assert [fu for fu in report.follow_ups if fu.kind == "window_extension"] == []
