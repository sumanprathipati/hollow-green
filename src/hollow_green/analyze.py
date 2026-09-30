"""Orchestrator: ingest -> buffers -> score -> follow-ups -> classify -> tolerance."""

from hollow_green import detectors
from hollow_green.buffers import compute_buffers
from hollow_green.classify import classify
from hollow_green.followups import build_follow_ups, build_rollback_summary
from hollow_green.ingest import terminal_label, validate_and_sort
from hollow_green.schemas import ReleaseLog, ReleaseReport
from hollow_green.scoring import compute_score
from hollow_green.tolerance import compute_tolerance


def analyze_log(log: ReleaseLog) -> ReleaseReport:
    events = validate_and_sort(log)
    terminal_kind = terminal_label(events)
    buffers = compute_buffers(log, events)
    rollback_summary = build_rollback_summary(events)
    score = compute_score(log, events, buffers, terminal_kind)
    follow_ups = build_follow_ups(
        events,
        buffers,
        rollback_summary,
        log.retry_budget_max,
        terminal_kind,
        float(log.window_minutes),
    )
    classification = classify(
        terminal_kind,
        score.reserve_level,
        buffers.health_end,
        buffers.rollback_available,
        buffers.manual_count,
        events,
    )
    tolerance = compute_tolerance(score.reserve_level, buffers, rollback_summary)
    _ = detectors.has_recovery_action(events)
    return ReleaseReport(
        release_id=log.release_id,
        classification=classification,  # type: ignore[arg-type]
        terminal=terminal_kind,  # type: ignore[arg-type]
        score=score,
        follow_ups=follow_ups,
        rollback_summary=rollback_summary,
        tolerance=tolerance,
    )


def analyze_release(payload: dict[str, object]) -> ReleaseReport:
    log = ReleaseLog.model_validate(payload)
    return analyze_log(log)
