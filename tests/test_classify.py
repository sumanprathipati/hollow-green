"""All five release classes."""

from conftest import analyze_fixture


def test_clean_success():
    assert analyze_fixture("synthetic_clean_001.json").classification == "clean_success"


def test_recovered_success():
    r = analyze_fixture("synthetic_recovered_002.json")
    assert r.classification == "recovered_success"


def test_fragile_success():
    assert analyze_fixture("synthetic_fragile_003.json").classification == "fragile_success"
    assert analyze_fixture("synthetic_bypass_004.json").classification == "fragile_success"


def test_rollback():
    assert analyze_fixture("synthetic_rollback_005.json").classification == "rollback"
    assert analyze_fixture("synthetic_rollback_unverified_005b.json").classification == "rollback"


def test_failed():
    assert analyze_fixture("synthetic_failed_006.json").classification == "failed"
