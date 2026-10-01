"""Pure mapping tests for public GitHub evidence (no HTTP)."""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, "src")

from hollow_green.analyze import analyze_log
from hollow_green.public_data import (
    BASE_LIMITATIONS,
    DISCLAIMER,
    UNAVAILABLE_SIGNALS,
    CommitRef,
    map_evidence_to_release_log,
    sanitize_id,
    select_candidate,
)

FIXTURE = Path(__file__).parent / "fixtures" / "github" / "octocat__Hello-World.json"


def test_sanitize_id():
    assert sanitize_id("v1.0") == "v1-0"
    assert sanitize_id("octocat/Hello-World") == "octocat-hello-world"
    assert sanitize_id("  ") == "candidate"


def test_select_candidate_prefers_release():
    raw = json.loads(FIXTURE.read_text())
    candidate = select_candidate(
        raw["/repos/octocat/Hello-World/releases"],
        raw["/repos/octocat/Hello-World/tags"],
        raw["/repos/octocat/Hello-World/commits"],
        "https://github.com/octocat/Hello-World",
    )
    assert candidate.kind == "release"
    assert candidate.candidate_id == "v1-0"
    assert candidate.url.startswith("https://github.com/")


def test_select_candidate_skips_drafts():
    releases = [
        {"tag_name": "v9", "draft": True, "html_url": "https://example.test/r"},
    ]
    tags = [{"name": "v1.0"}]
    candidate = select_candidate(releases, tags, [], "https://example.test/r")
    assert candidate.kind == "tag"


def test_select_candidate_none_when_empty():
    candidate = select_candidate([], [], [], "https://example.test/r")
    assert candidate.kind == "none"


def test_map_produces_valid_log_with_source_urls():
    retrieved_at = datetime(2026, 1, 20, tzinfo=UTC)
    candidate = select_candidate([], [], [], "https://example.test/r")
    assert candidate.kind == "none"
    real = select_candidate(
        [
            {
                "tag_name": "v1.0",
                "name": "First release",
                "html_url": "https://github.com/octocat/Hello-World/releases/tag/v1.0",
                "published_at": "2026-01-15T12:00:00Z",
            }
        ],
        [],
        [],
        "https://github.com/octocat/Hello-World",
    )
    commits = [
        CommitRef(
            sha="aaa111",
            message="Initial commit",
            date=datetime(2026, 1, 10, 10, 0, tzinfo=UTC),
            url="https://github.com/octocat/Hello-World/commit/aaa111",
        )
    ]
    log = map_evidence_to_release_log(
        "octocat/Hello-World",
        real,
        commits,
        "https://github.com/octocat/Hello-World",
        retrieved_at,
    )
    assert log.release_id.startswith("github-octocat-hello-world-")
    types = [e.type for e in log.events]
    assert types.count("deploy_started") == 1
    assert "deploy_succeeded" in types
    assert len({e.event_id for e in log.events}) == len(log.events)
    assert all(e.release_id == log.release_id for e in log.events)
    urls = [str(e.details.get("source_url")) for e in log.events]
    assert all(u.startswith("https://github.com/") for u in urls)
    assert "health_report" not in types
    assert not any(t.startswith("rollback") for t in types)
    report = analyze_log(log)
    # 5-day span vs fixed 60m demo window: time.low (15) + time.critical (10).
    assert report.score.reserve_level == 75
    assert report.score.recovery_load == "medium"
    assert {d.rule_id for d in report.score.deductions} == {"time.low", "time.critical"}
    assert report.score.buffers.health_end == "unknown"


def test_limitations_and_unavailable_documented():
    assert DISCLAIMER.startswith("Public repository evidence only")
    assert "health" in UNAVAILABLE_SIGNALS
    assert "rollback" in UNAVAILABLE_SIGNALS
    assert "production_telemetry" in UNAVAILABLE_SIGNALS
    assert any("not a production deploy" in lim for lim in BASE_LIMITATIONS)
