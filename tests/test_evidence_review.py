"""Evidence-review unit tests: bundle, prompt, validator. No live calls."""

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, "src")


from api.public_data import build_assessment
from hollow_green import evidence_review as er

FIXTURE = Path(__file__).parent / "fixtures" / "github" / "octocat__Hello-World.json"


def load_bundle() -> tuple[er.EvidenceBundle, dict[str, object]]:
    raw: dict[str, object] = json.loads(FIXTURE.read_text())
    assessment = build_assessment(raw, "octocat", "Hello-World", "fixture", None)
    return er.build_evidence_bundle(assessment), assessment


def valid_output(bundle: er.EvidenceBundle) -> dict[str, object]:
    by_id = {r.id: r for r in bundle.records}
    cited = ["E1", "E2", "E3", "E6", "E7", "E9"]
    sections = {
        "evidence_summary": [
            {
                "text": "Repository octocat/Hello-World shows 3 recent commits [E1] [E3].",
                "citation_ids": ["E1", "E3"],
            },
            {
                "text": "Candidate release 'First release' was published on 2026-01-15 [E2].",
                "citation_ids": ["E2"],
            },
            {
                "text": "2 pull requests are recorded, 1 open and 1 closed [E6] [E7].",
                "citation_ids": ["E6", "E7"],
            },
        ],
        "deterministic_assessment_explanation": [
            {
                "text": (
                    "The deterministic result is elevated change risk "
                    "with sufficient evidence [E2] [E9]."
                ),
                "citation_ids": ["E2", "E9"],
            }
        ],
        "evidence_gaps": [
            {
                "text": "No public evidence was available for health or rollback status [E9].",
                "citation_ids": ["E9"],
            },
            {
                "text": "CI results and production telemetry cannot be determined here [E9].",
                "citation_ids": ["E9"],
            },
        ],
        "human_review_checks": [
            {
                "text": "Confirm CI status in the organization's internal system.",
                "citation_ids": [],
            },
            {
                "text": "Review the cited commit and pull request sources before acting.",
                "citation_ids": [],
            },
        ],
    }
    sources = [
        {"id": cid, "label": by_id[cid].label, "url": by_id[cid].url, "kind": by_id[cid].kind}
        for cid in cited
    ]
    return {"sections": sections, "sources": sources}


def test_bundle_uses_only_approved_fields_and_caps():
    bundle, _ = load_bundle()
    assert bundle.record_count == len(bundle.records) == 10
    assert bundle.input_chars > 0
    kinds = [r.kind for r in bundle.records]
    assert kinds.count("commit") <= 5
    assert kinds.count("pull_request") <= 5
    assert kinds.count("issue") <= 5
    ids = [r.id for r in bundle.records]
    assert ids == [f"E{i}" for i in range(1, 11)]
    assert len(set(ids)) == len(ids)
    dumped = json.dumps(bundle.model_dump(mode="json")).lower()
    for secret in ("token", "bearer", "authorization", "secret", "password", "cookie"):
        assert secret not in dumped
    for record in bundle.records:
        assert record.url.startswith("https://")
        assert len(record.label) <= 200
        for value in record.facts.values():
            assert len(value) <= 121


def test_bundle_urls_come_only_from_assessment():
    bundle, assessment = load_bundle()
    allowed = set()
    evidence = assessment["evidence"]
    assert isinstance(evidence, dict)
    allowed.add(str(evidence.get("repo_url")))
    for key in ("commits_recent", "pulls_recent", "issues_open_sample"):
        items = evidence.get(key)
        assert isinstance(items, list)
        for item in items:
            assert isinstance(item, dict)
            allowed.add(str(item.get("url")))
    candidate = assessment["candidate"]
    assert isinstance(candidate, dict)
    allowed.add(str(candidate.get("url")))
    for record in bundle.records:
        assert record.url in allowed, record.url


def test_prompt_contains_rules_and_no_secrets():
    bundle, _ = load_bundle()
    system, user = er.build_review_prompt(bundle)
    assert bundle.change_risk_level in system
    assert bundle.public_recommendation in system
    assert "clean_success" in system
    assert "[E1]" in system
    assert "350" in system and "4 bullets" in system
    assert "JSON only" in system
    lowered = (system + user).lower()
    for secret in ("github_token", "bearer", "authorization", "api_key"):
        assert secret not in lowered
    payload = json.loads(user)
    assert set(payload["records"][0].keys()) == {"id", "kind", "label", "url", "facts"}
    assert len(user) <= er.MAX_PROMPT_CHARS


def test_valid_output_accepted():
    bundle, _ = load_bundle()
    assert er.validate_review_output(valid_output(bundle), bundle) == []


def mutate(bundle: er.EvidenceBundle, path: str, value: object) -> dict[str, object]:
    out = copy.deepcopy(valid_output(bundle))
    target: object = out
    keys = path.split(".")
    for key in keys[:-1]:
        assert isinstance(target, dict)
        child = target[key]
        target = child
    assert isinstance(target, dict)
    target[keys[-1]] = value
    return out


def test_reject_unknown_citation():
    bundle, _ = load_bundle()
    out = mutate(
        bundle,
        "sections.evidence_summary",
        [{"text": "Something happened [E99].", "citation_ids": ["E99"]}],
    )
    issues = er.validate_review_output(out, bundle)
    assert any("unknown source" in i for i in issues)


def test_reject_missing_citation():
    bundle, _ = load_bundle()
    out = mutate(
        bundle,
        "sections.evidence_summary",
        [{"text": "Repository shows 3 recent commits.", "citation_ids": []}],
    )
    issues = er.validate_review_output(out, bundle)
    assert any("missing citations" in i for i in issues)


def test_reject_invented_url_and_markdown_and_html():
    bundle, _ = load_bundle()
    for bad in (
        "See https://example.test/evil for details [E1].",
        "See [details](https://example.test/evil) here [E1].",
        "See <a href='https://example.test'>x</a> here [E1].",
    ):
        out = mutate(bundle, "sections.evidence_summary", [{"text": bad, "citation_ids": ["E1"]}])
        issues = er.validate_review_output(out, bundle)
        assert any("URL, link, or HTML" in i for i in issues), bad


def test_reject_unlisted_source_url():
    bundle, _ = load_bundle()
    out = valid_output(bundle)
    assert isinstance(out["sources"], list)
    out["sources"][0]["url"] = "https://example.test/swapped"
    issues = er.validate_review_output(out, bundle)
    assert any("does not match bundle" in i for i in issues)


def test_reject_forbidden_wording():
    bundle, _ = load_bundle()
    cases = [
        "You may proceed after review [E1].",
        "This is PROCEED WITH CAUTION territory [E1].",
        "The release failed last night [E1].",
        "Classification looks like clean_success [E1].",
        "We grant deployment approval here [E1].",
        "It is safe to deploy now [E1].",
    ]
    for bad in cases:
        out = mutate(bundle, "sections.evidence_summary", [{"text": bad, "citation_ids": ["E1"]}])
        issues = er.validate_review_output(out, bundle)
        assert any("forbidden wording" in i for i in issues), bad


def test_reject_altered_recommendation_and_risk():
    bundle, _ = load_bundle()
    out = mutate(
        bundle,
        "sections.deterministic_assessment_explanation",
        [
            {
                "text": "The result should be LOWER CHANGE RISK — REVIEW REQUIRED [E2].",
                "citation_ids": ["E2"],
            }
        ],
    )
    issues = er.validate_review_output(out, bundle)
    assert any("alters the deterministic recommendation" in i for i in issues)
    out = mutate(
        bundle,
        "sections.deterministic_assessment_explanation",
        [{"text": "The change risk here is low and manageable [E2].", "citation_ids": ["E2"]}],
    )
    issues = er.validate_review_output(out, bundle)
    assert any("contradicts change_risk_level" in i for i in issues)


def test_reject_unsupported_facts():
    bundle, _ = load_bundle()
    cases = [
        "There were 9 commits last week [E3].",
        "The release shipped on 2025-12-31 [E2].",
        "Commit deadbee1 introduced the change [E3].",
        "Issue #99 blocks this work [E8].",
        "About 50% of commits are recent [E3].",
    ]
    for bad in cases:
        out = mutate(
            bundle,
            "sections.evidence_summary",
            [{"text": bad, "citation_ids": ["E3"] if "E3" in bad or "commits" in bad else ["E2"]}],
        )
        # fix citations to valid ones for the date/sha/count cases
        issues = er.validate_review_output(out, bundle)
        assert issues, bad


def test_reject_uncited_factual_check():
    bundle, _ = load_bundle()
    out = mutate(
        bundle,
        "sections.human_review_checks",
        [
            {
                "text": "Confirm CI for octocat/Hello-World in the internal system.",
                "citation_ids": [],
            }
        ],
    )
    issues = er.validate_review_output(out, bundle)
    assert any("without citations" in i for i in issues)


def test_reject_bullet_and_word_caps_and_empty_section():
    bundle, _ = load_bundle()
    many = [{"text": f"Observation {i} here [E1].", "citation_ids": ["E1"]} for i in range(5)]
    out = mutate(bundle, "sections.evidence_gaps", many)
    assert any("exceeds 4 bullets" in i for i in er.validate_review_output(out, bundle))
    out = mutate(bundle, "sections.evidence_gaps", [])
    assert any("is empty" in i for i in er.validate_review_output(out, bundle))
    long_text = "word " * 320
    out = mutate(
        bundle,
        "sections.evidence_summary",
        [{"text": long_text.strip() + " [E1].", "citation_ids": ["E1"]}],
    )
    assert any("exceeds 350 words" in i for i in er.validate_review_output(out, bundle))


def test_reject_malformed_and_missing_section():
    bundle, _ = load_bundle()
    assert er.validate_review_output({"nope": 1}, bundle) != []
    out = valid_output(bundle)
    assert isinstance(out["sections"], dict)
    del out["sections"]["evidence_gaps"]
    assert er.validate_review_output(out, bundle) != []
    out = valid_output(bundle)
    out["unexpected"] = True
    assert er.validate_review_output(out, bundle) != []


def test_reject_citation_missing_from_sources():
    bundle, _ = load_bundle()
    out = valid_output(bundle)
    assert isinstance(out["sources"], list)
    out["sources"] = [s for s in out["sources"] if s["id"] != "E9"]
    issues = er.validate_review_output(out, bundle)
    assert any("missing from sources" in i for i in issues)
