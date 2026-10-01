"""Public-result vocabulary tests: computed only from observable public data."""

import sys
from datetime import UTC, datetime, timedelta

sys.path.insert(0, "src")

from hollow_green.public_data import (
    DEPLOYMENT_READINESS,
    CandidateInfo,
    CommitRef,
    RepositoryEvidence,
    compute_public_result,
)


def make_evidence(
    kind: str = "release",
    age_days: int | None = 5,
    commits: int = 3,
    open_prs: int = 1,
    open_issues: int = 2,
    with_dates: bool = True,
) -> RepositoryEvidence:
    retrieved_at = datetime(2026, 1, 20, tzinfo=UTC)
    published_at = (
        retrieved_at - timedelta(days=age_days)
        if age_days is not None and with_dates and kind != "none"
        else None
    )
    commit_refs = [
        CommitRef(
            sha=f"sha{i:03d}",
            message=f"commit {i}",
            date=(retrieved_at - timedelta(days=i + 1)) if with_dates else None,
            url=f"https://github.com/o/r/commit/sha{i:03d}",
        )
        for i in range(commits)
    ]
    pulls = [
        {
            "number": i,
            "title": f"pr {i}",
            "state": "open" if i < open_prs else "closed",
            "url": f"https://github.com/o/r/pull/{i}",
        }
        for i in range(max(open_prs, 1 if commits == 0 else 0))
    ]
    from hollow_green.public_data import IssueRef, PullRef

    return RepositoryEvidence(
        repo_full_name="o/r",
        repo_url="https://github.com/o/r",
        candidate=CandidateInfo(
            candidate_id="v1-0" if kind != "none" else "no-candidate",
            kind=kind,
            name="v1.0",
            published_at=published_at,
            url="https://github.com/o/r/releases/tag/v1.0",
        ),
        commits_recent=commit_refs,
        pulls_recent=[
            PullRef(number=p["number"], title=p["title"], state=p["state"], url=p["url"])
            for p in pulls
        ],
        issues_open_sample=[IssueRef(number=1, title="bug", url="https://github.com/o/r/issues/1")]
        if open_issues > 0
        else [],
        retrieved_at=retrieved_at,
        source_urls=["https://api.github.com/repos/o/r"],
        open_issues_count=open_issues,
    )


def test_low_risk_old_quiet_repo():
    result = compute_public_result(make_evidence(age_days=90, commits=1, open_prs=0, open_issues=0))
    assert result.change_risk_level == "low"
    assert result.public_recommendation == "LOWER CHANGE RISK — REVIEW REQUIRED"
    assert result.deployment_readiness == DEPLOYMENT_READINESS


def test_moderate_risk_recent_activity():
    result = compute_public_result(make_evidence(age_days=20, commits=2, open_prs=0, open_issues=1))
    assert result.change_risk_level == "moderate"
    assert result.public_recommendation == "MODERATE CHANGE RISK — REVIEW EVIDENCE"


def test_elevated_risk_fresh_or_busy():
    result = compute_public_result(make_evidence(age_days=2, commits=1, open_prs=0, open_issues=0))
    assert result.change_risk_level == "elevated"
    assert result.public_recommendation == "ELEVATED CHANGE RISK — INVESTIGATE"


def test_insufficient_evidence_unknown():
    evidence = make_evidence(kind="none", commits=0, open_prs=0, open_issues=0, with_dates=False)
    result = compute_public_result(evidence)
    assert result.change_risk_level == "unknown"
    assert result.evidence_completeness == "insufficient"
    assert result.public_recommendation == "INSUFFICIENT EVIDENCE — DO NOT INFER READINESS"
    assert result.deployment_readiness == DEPLOYMENT_READINESS


def test_missing_signals_affect_completeness_not_health():
    evidence = make_evidence(age_days=90, commits=0, open_prs=0, open_issues=0)
    result = compute_public_result(evidence)
    assert result.evidence_completeness in ("limited", "insufficient")
    assert result.deployment_readiness == DEPLOYMENT_READINESS
    for banned in ("PROCEED", "ROLLBACK VERIFIED", "HOLD / INVESTIGATE"):
        assert banned not in result.public_recommendation
